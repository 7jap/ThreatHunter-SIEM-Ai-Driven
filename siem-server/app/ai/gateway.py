import abc
from typing import Dict, Any, List

class AIProviderInterface(abc.ABC):
    @abc.abstractmethod
    async def analyze_alert(self, alert_data: Dict[str, Any], context_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyzes an alert given its context and returns a structured response.
        Expected format:
        {
            "verdict": "MALICIOUS" | "BENIGN" | "SUSPICIOUS",
            "confidence": 0-100,
            "explanation": "Detailed explanation of the findings",
            "recommended_actions": ["Action 1", "Action 2"]
        }
        """
        pass

class MockOllamaProvider(AIProviderInterface):
    """
    A temporary mock provider to simulate Local Ollama before actual integration.
    """
    def __init__(self, endpoint: str = "http://localhost:11434"):
        self.endpoint = endpoint

    async def analyze_alert(self, alert_data: Dict[str, Any], context_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        import asyncio
        import random
        # Simulate LLM thinking time
        await asyncio.sleep(random.uniform(2.0, 5.0))
        
        verdicts = ["MALICIOUS", "BENIGN", "SUSPICIOUS"]
        chosen_verdict = random.choice(verdicts)
        
        return {
            "verdict": chosen_verdict,
            "confidence": random.randint(60, 99),
            "explanation": f"Based on the analysis of signature '{alert_data.get('signature')}' and {len(context_alerts)} related historical alerts, this activity is considered {chosen_verdict}.",
            "recommended_actions": [
                "Isolate the source IP" if chosen_verdict == "MALICIOUS" else "Monitor for further activity",
                "Review firewall rules"
            ],
            "raw_response": "Simulated response from Local Ollama Provider"
        }

class LocalOllamaProvider(AIProviderInterface):
    """
    Real integration with a local Ollama instance.
    """
    def __init__(self, endpoint: str = "http://localhost:11434", model: str = "llama3"):
        self.endpoint = endpoint
        self.model = model

    async def analyze_alert(self, alert_data: Dict[str, Any], context_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        import json
        import urllib.request
        import asyncio

        prompt = f"""
You are a SOC L3 Analyst. Analyze this security alert and provide a JSON response.
Alert: {json.dumps(alert_data)}
Context (Last {len(context_alerts)} alerts from this IP): {json.dumps(context_alerts)}

Respond strictly in the following JSON format:
{{
    "verdict": "MALICIOUS" or "BENIGN" or "SUSPICIOUS",
    "confidence": <number between 0 and 100>,
    "explanation": "<your detailed analysis>",
    "recommended_actions": ["<action1>", "<action2>"]
}}
"""
        req_body = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }
        
        req = urllib.request.Request(
            f"{self.endpoint}/api/generate",
            data=json.dumps(req_body).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )

        def _make_req():
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    return response.read().decode('utf-8')
            except Exception as e:
                return str(e)
                
        try:
            raw_res = await asyncio.to_thread(_make_req)
            data = json.loads(raw_res)
            llm_response = data.get("response", "{}")
            parsed = json.loads(llm_response)
            parsed["raw_response"] = llm_response
            return parsed
        except Exception as e:
            # Fallback to mock on error (e.g. Ollama not running)
            print(f"[AI Gateway] Ollama failed: {e}. Falling back to mock.")
            mock = MockOllamaProvider()
            return await mock.analyze_alert(alert_data, context_alerts)

class GeminiProvider(AIProviderInterface):
    """
    Integration with Google Gemini API.
    """
    def __init__(self, endpoint: str = "https://generativelanguage.googleapis.com/v1beta/models", model: str = "gemini-flash-latest", api_key: str = ""):
        self.endpoint = endpoint
        self.model = model
        self.api_key = api_key

    async def analyze_alert(self, alert_data: Dict[str, Any], context_alerts: List[Dict[str, Any]]) -> Dict[str, Any]:
        import json
        import urllib.request
        import asyncio

        prompt = f"""
You are a SOC L3 Analyst. Analyze this security alert and provide a JSON response.
Alert: {json.dumps(alert_data)}
Context (Last {len(context_alerts)} alerts from this IP): {json.dumps(context_alerts)}

Respond strictly in the following JSON format without any markdown wrappers:
{{
    "verdict": "MALICIOUS" or "BENIGN" or "SUSPICIOUS",
    "confidence": <number between 0 and 100>,
    "explanation": "<your detailed analysis>",
    "recommended_actions": ["<action1>", "<action2>"]
}}
"""
        req_body = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt}
                    ]
                }
            ]
        }
        
        endpoint = self.endpoint.rstrip('/')
        url = f"{endpoint}/{self.model}:generateContent"
        
        req = urllib.request.Request(
            url,
            data=json.dumps(req_body).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'X-goog-api-key': self.api_key
            }
        )

        def _make_req():
            import urllib.error
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    return response.read().decode('utf-8')
            except urllib.error.HTTPError as e:
                err_body = e.read().decode('utf-8')
                raise Exception(f"Gemini API Error ({e.code}): {err_body}")
            except Exception as e:
                raise Exception(f"Connection Error: {str(e)}")
                
        try:
            raw_res = await asyncio.to_thread(_make_req)
            data = json.loads(raw_res)
            
            # Extract response text
            candidates = data.get("candidates", [])
            if not candidates:
                raise ValueError("No response from Gemini")
                
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
            
            # Clean up markdown formatting if Gemini added it
            text = text.replace('```json', '').replace('```', '').strip()
            
            parsed = json.loads(text)
            parsed["raw_response"] = raw_res
            return parsed
        except Exception as e:
            print(f"[AI Gateway] Gemini failed: {e}. Falling back to mock.")
            mock = MockOllamaProvider()
            return await mock.analyze_alert(alert_data, context_alerts)

def get_ai_provider(provider_name: str = "ollama", config: dict = None) -> AIProviderInterface:
    config = config or {}
    provider_name = provider_name.lower()
    
    if "gemini" in provider_name:
        endpoint = config.get("endpoint") or "https://generativelanguage.googleapis.com/v1beta/models"
        model = config.get("model") or "gemini-flash-latest"
        api_key = config.get("api_key") or ""
        return GeminiProvider(endpoint=endpoint, model=model, api_key=api_key)
    else:
        endpoint = config.get("endpoint") or "http://localhost:11434"
        model = config.get("model") or "llama3"
        return LocalOllamaProvider(endpoint=endpoint, model=model)
