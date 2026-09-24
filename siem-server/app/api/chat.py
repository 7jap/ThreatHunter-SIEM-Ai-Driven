from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from pydantic import BaseModel
from datetime import datetime, timezone
import json
import urllib.request
import urllib.error
import asyncio

from app.database.session import get_db
from app.database.models.events import Alert, AlertAIAnalysis
from app.database.models.ai import AIProvider
from app.api.deps import RequirePermissions, get_current_user
from app.database.models.users import User
from app.core.permissions import Permissions

router = APIRouter()

class ChatMessage(BaseModel):
    role: str
    text: str

class ChatRequest(BaseModel):
    message: str
    history: list[ChatMessage] = []

def format_relative_time(ts: datetime | None, now: datetime) -> str:
    if not ts:
        return "Unknown timestamp"
    t = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
    n = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
    diff = int((n - t).total_seconds())
    if diff < 0:
        return f"just now ({t.strftime('%H:%M:%S UTC')})"
    if diff < 60:
        return f"{diff}s ago ({t.strftime('%H:%M:%S UTC')})"
    if diff < 3600:
        m = diff // 60
        s = diff % 60
        return f"{m}m {s}s ago ({t.strftime('%H:%M:%S UTC')})"
    h = diff // 3600
    m = (diff % 3600) // 60
    return f"{h}h {m}m ago ({t.strftime('%Y-%m-%d %H:%M:%S UTC')})"

@router.post("/")
async def chat_with_ai(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    
    # 1. Fetch recent alerts (top 10)
    result = await db.execute(
        select(Alert)
        .order_by(Alert.timestamp.desc())
        .limit(10)
    )
    recent_alerts = list(result.scalars().all())
    
    # 2. Dynamic Search: If user query references a signature, IP, or ID, fetch matching alerts from DB
    query_text = req.message.strip()
    matched_alerts = []
    
    # Extract clean search tokens (longer than 3 chars)
    stop_words = {'explain', 'about', 'alert', 'alerts', 'this', 'that', 'what', 'when', 'where', 'which', 'show', 'tell', 'seconds', 'minutes', 'hours'}
    tokens = [t for t in query_text.replace('"', '').replace("'", "").split() if len(t) > 3 and t.lower() not in stop_words]
    
    if tokens:
        # Search by full phrase first, or individual tokens
        from sqlalchemy import or_
        filters = []
        # If phrase has multiple words like "ET MALWARE", search phrase
        filters.append(Alert.signature.ilike(f"%{query_text[:50]}%"))
        for tok in tokens[:4]:
            filters.append(Alert.signature.ilike(f"%{tok}%"))
            filters.append(Alert.source_ip.ilike(f"%{tok}%"))
            filters.append(Alert.destination_ip.ilike(f"%{tok}%"))
            filters.append(Alert.id.ilike(f"%{tok}%"))
            
        search_res = await db.execute(
            select(Alert)
            .where(or_(*filters))
            .order_by(Alert.timestamp.desc())
            .limit(5)
        )
        found = search_res.scalars().all()
        for a in found:
            if not any(r.id == a.id for r in recent_alerts):
                matched_alerts.append(a)
    
    # Format rich alert lines
    sev_symbols = {1: "🔴 CRITICAL/HIGH", 2: "🟠 MEDIUM", 3: "🔵 LOW"}
    
    def format_line(idx, a):
        rel = format_relative_time(a.timestamp, now)
        sev = sev_symbols.get(a.severity, f"LEVEL-{a.severity}")
        src = f"{a.source_ip}:{a.source_port}" if a.source_port else a.source_ip
        dst = f"{a.destination_ip}:{a.destination_port}" if a.destination_port else a.destination_ip
        proto = a.protocol or "IP"
        return f"{idx}. [Alert {a.id[:8]}] ⏱️ {rel} | {sev} | Rule: \"{a.signature}\" | 🌐 {src} ➔ {dst} ({proto}) | Status: {a.status}"

    recent_lines = [format_line(i + 1, a) for i, a in enumerate(recent_alerts)]
    context_str = "\n".join(recent_lines) if recent_lines else "No active alerts in the telemetry stream."
    
    if matched_alerts:
        matched_lines = [format_line(i + 1, a) for i, a in enumerate(matched_alerts)]
        context_str += "\n\nSPECIFIC ALERTS MATCHING INQUIRY:\n" + "\n".join(matched_lines)
        
    # 2. Get AI Providers
    providers_res = await db.execute(
        select(AIProvider)
        .where(AIProvider.is_enabled == True)
        .order_by(AIProvider.is_default.desc(), AIProvider.id)
    )
    enabled_providers = providers_res.scalars().all()
    
    if not enabled_providers:
        return {"response": "System Notice: No active AI provider is configured. Please configure an AI in settings."}

    # 3. Build System Prompt & Instructions
    system_prompt = f"""You are an elite Lead SOC Analyst & Cyber Threat Hunter for SIEM Core 🛡️.
You have real-time access to the SIEM telemetry feed and database.

CURRENT SERVER TIME: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}

LIVE TELEMETRY (Last {len(recent_alerts)} Alerts, ordered newest to oldest):
{context_str}

STRICT ANALYST DIRECTIVES:
1. Persona: Sharp, technical, authoritative cybersecurity expert.
2. Formatting: Ultra-clean Markdown with bullet points, bold keywords, and emojis (🚨, 🛡️, ⚠️, 🔍, ⏱️, 💻, 🎯, 📊).
3. Speed & Brevity: Be concise and direct. Do not repeat long boilerplate greetings or caveats. Give immediate answers.
4. Timing & Recency: When the user asks about time (e.g. "how many seconds ago?"), use the exact relative time and seconds provided in the telemetry above.
5. Grounding: You ALREADY have the alerts right above. NEVER claim you lack alert details or ask the user to provide an alert ID.
6. Language: Match the user's language (Arabic ➔ Arabic, English ➔ English).
"""

    # Build Native Messages Array
    gemini_contents = []
    ollama_messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Append history
    is_first_gemini = True
    for msg in req.history[-5:]:
        # Ollama
        ollama_messages.append({"role": "assistant" if msg.role == "ai" else "user", "content": msg.text})
        
        # Gemini
        g_role = "model" if msg.role == "ai" else "user"
        g_text = msg.text
        if is_first_gemini and g_role == "user":
            g_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUser: {g_text}"
            is_first_gemini = False
        gemini_contents.append({"role": g_role, "parts": [{"text": g_text}]})
        
    # Current User Message
    ollama_messages.append({"role": "user", "content": req.message})
    
    g_text_current = req.message
    if is_first_gemini:
        g_text_current = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUser: {g_text_current}"
    gemini_contents.append({"role": "user", "parts": [{"text": g_text_current}]})
    
    async def call_gemini(config, timeout_sec=20):
        req_body = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 600
            }
        }
        
        endpoint = config['endpoint'].rstrip('/')
        url = f"{endpoint}/{config['model']}:generateContent"
        
        request = urllib.request.Request(
            url,
            data=json.dumps(req_body).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'X-goog-api-key': config['api_key']}
        )
        def _make():
            try:
                with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                    return response.read().decode('utf-8')
            except urllib.error.HTTPError as e:
                err_body = e.read().decode('utf-8')
                raise Exception(f"Gemini API Error ({e.code}): {err_body}")
            except Exception as e:
                raise Exception(f"Connection Error: {str(e)}")
                
        raw = await asyncio.to_thread(_make)
        data = json.loads(raw)
        return data.get("candidates", [])[0].get("content", {}).get("parts", [{}])[0].get("text", "I'm sorry, I couldn't generate a response.")
            
    async def call_ollama(config, timeout_sec=20):
        req_body = {
            "model": config['model'],
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 400
            }
        }
        request = urllib.request.Request(
            f"{config['endpoint']}/api/chat",
            data=json.dumps(req_body).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        def _make():
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                return response.read().decode('utf-8')
        raw = await asyncio.to_thread(_make)
        data = json.loads(raw)
        return data.get("message", {}).get("content", "I'm sorry, I couldn't generate a response.")

    last_error = ""
    for provider in enabled_providers:
        try:
            config = {
                "endpoint": provider.endpoint,
                "model": provider.model,
                "api_key": provider.api_key_encrypted
            }
            current_timeout = 35 if provider.is_default else 15
            
            if "gemini" in provider.name.lower():
                response_text = await call_gemini(config, current_timeout)
            else:
                response_text = await call_ollama(config, current_timeout)
            return {"response": response_text}
        except Exception as e:
            last_error = str(e)
            continue
            
    return {"response": f"Error: All configured AI Providers failed. Last error: {last_error}"}

@router.post("/alert/{alert_id}")
async def chat_about_alert(
    alert_id: str,
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    now = datetime.now(timezone.utc)
    
    # Fetch Alert
    alert_res = await db.execute(select(Alert).where(Alert.id == alert_id))
    alert = alert_res.scalars().first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
        
    ai_res = await db.execute(select(AlertAIAnalysis).where(AlertAIAnalysis.alert_id == alert_id))
    ai_analysis = ai_res.scalars().first()
    
    rel_time = format_relative_time(alert.timestamp, now)
    sev_symbols = {1: "🔴 CRITICAL/HIGH", 2: "🟠 MEDIUM", 3: "🔵 LOW"}
    sev_label = sev_symbols.get(alert.severity, f"LEVEL-{alert.severity}")
    src = f"{alert.source_ip}:{alert.source_port}" if alert.source_port else alert.source_ip
    dst = f"{alert.destination_ip}:{alert.destination_port}" if alert.destination_port else alert.destination_ip
    
    alert_context = f"""
ALERT SPECIFICATIONS:
- Alert ID: {alert.id}
- Detection Time: ⏱️ {rel_time}
- Severity: {sev_label}
- Signature / Detection: "{alert.signature}"
- Protocol: {alert.protocol or 'TCP/IP'}
- Connection Path: 🌐 {src} ➔ {dst}
- Current Status: {alert.status}
"""
    if ai_analysis:
        alert_context += f"""
PRIOR AI TRIAGE:
- Verdict: {ai_analysis.summary} (Confidence: {ai_analysis.confidence}%)
- Technical Explanation: {ai_analysis.explanation}
- Recommended Actions: {json.dumps(ai_analysis.recommended_actions)}
"""
        
    providers_res = await db.execute(
        select(AIProvider)
        .where(AIProvider.is_enabled == True)
        .order_by(AIProvider.is_default.desc(), AIProvider.id)
    )
    enabled_providers = providers_res.scalars().all()
    
    if not enabled_providers:
        return {"response": "System Notice: No active AI provider is configured."}

    system_prompt = f"""You are an elite Lead SOC Analyst & Threat Hunter for SIEM Core 🛡️ investigating a specific alert.
You have the full alert dossier below:

{alert_context}

INVESTIGATION DIRECTIVES:
1. Provide sharp, technical, and actionable security insights.
2. Formatting: Clean Markdown, concise bullet points, and cybersecurity emojis (🛡️, 🚨, ⚠️, 🔍, ⏱️, 💻, 🎯).
3. Do not ask for alert details; you already have the full telemetry.
4. Keep answers concise, rapid, and directly address the analyst's question.
5. Language: Match the user's language (Arabic ➔ Arabic, English ➔ English).
"""

    gemini_contents = []
    ollama_messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    is_first_gemini = True
    for msg in req.history[-5:]:
        ollama_messages.append({"role": "assistant" if msg.role == "ai" else "user", "content": msg.text})
        
        g_role = "model" if msg.role == "ai" else "user"
        g_text = msg.text
        if is_first_gemini and g_role == "user":
            g_text = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUser: {g_text}"
            is_first_gemini = False
            
        gemini_contents.append({"role": g_role, "parts": [{"text": g_text}]})
        
    ollama_messages.append({"role": "user", "content": req.message})
    
    g_text_current = req.message
    if is_first_gemini:
        g_text_current = f"SYSTEM INSTRUCTIONS:\n{system_prompt}\n\nUser: {g_text_current}"
    gemini_contents.append({"role": "user", "parts": [{"text": g_text_current}]})
    
    async def call_gemini(config, timeout_sec=20):
        req_body = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 600
            }
        }
        endpoint = config['endpoint'].rstrip('/')
        url = f"{endpoint}/{config['model']}:generateContent"
        
        request = urllib.request.Request(
            url,
            data=json.dumps(req_body).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'X-goog-api-key': config['api_key']}
        )
        def _make():
            try:
                with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                    return response.read().decode('utf-8')
            except urllib.error.HTTPError as e:
                err_body = e.read().decode('utf-8')
                raise Exception(f"Gemini API Error ({e.code}): {err_body}")
            except Exception as e:
                raise Exception(f"Connection Error: {str(e)}")
                
        raw = await asyncio.to_thread(_make)
        data = json.loads(raw)
        return data.get("candidates", [])[0].get("content", {}).get("parts", [{}])[0].get("text", "I'm sorry, I couldn't generate a response.")
            
    async def call_ollama(config, timeout_sec=20):
        req_body = {
            "model": config['model'],
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 400
            }
        }
        request = urllib.request.Request(
            f"{config['endpoint']}/api/chat",
            data=json.dumps(req_body).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        def _make():
            with urllib.request.urlopen(request, timeout=timeout_sec) as response:
                return response.read().decode('utf-8')
        raw = await asyncio.to_thread(_make)
        data = json.loads(raw)
        return data.get("message", {}).get("content", "I'm sorry, I couldn't generate a response.")

    last_error = ""
    for provider in enabled_providers:
        try:
            config = {
                "endpoint": provider.endpoint,
                "model": provider.model,
                "api_key": provider.api_key_encrypted
            }
            current_timeout = 35 if provider.is_default else 15
            
            if "gemini" in provider.name.lower():
                response_text = await call_gemini(config, current_timeout)
            else:
                response_text = await call_ollama(config, current_timeout)
            return {"response": response_text}
        except Exception as e:
            last_error = str(e)
            continue
            
    return {"response": f"Error: All configured AI Providers failed. Last error: {last_error}"}
