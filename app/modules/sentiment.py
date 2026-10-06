import json
from datetime import datetime, timezone
import httpx
from openai import AsyncOpenAI
from ..config import Settings
from .contracts import Signal

class SentimentAgent:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def collect(self, coin: str) -> dict:
        result: dict = {'coin': coin, 'sources': [], 'available': False}
        async with httpx.AsyncClient(timeout=20) as client:
            if self.settings.lunarcrush_api_key:
                response = await client.get(f'https://lunarcrush.com/api4/public/coins/{coin}/v1', headers={'Authorization': f'Bearer {self.settings.lunarcrush_api_key}'})
                if response.is_success:
                    result['lunarcrush'] = response.json()
                    result['sources'].append('LunarCrush')
            if self.settings.x_api_bearer_token:
                response = await client.get('https://api.x.com/2/tweets/search/recent', params={'query': f'({coin} OR ${coin}) lang:en -is:retweet','max_results':100,'tweet.fields':'created_at,public_metrics'}, headers={'Authorization': f'Bearer {self.settings.x_api_bearer_token}'})
                if response.is_success:
                    result['x'] = response.json()
                    result['sources'].append('X API')
        result['available'] = bool(result['sources'])
        return result

    async def analyze(self, coin: str) -> Signal:
        evidence = await self.collect(coin)
        if not evidence['available'] or not self.settings.openai_api_key:
            return Signal('ai', coin, 'UNAVAILABLE', 'LunarCrush/X veya OpenAI anahtarı eksik; karar üretilmedi.', source=', '.join(evidence['sources']))
        client = AsyncOpenAI(api_key=self.settings.openai_api_key)
        response = await client.chat.completions.create(model=self.settings.openai_model, temperature=0, response_format={'type':'json_object'}, messages=[{'role':'system','content':'Return JSON only with decision AL, SAT, or BEKLE and reason in Turkish. Do not invent facts; use only evidence.'},{'role':'user','content':json.dumps({'coin':coin,'window':'last 1 hour','evidence':evidence}, ensure_ascii=False)}])
        parsed = json.loads(response.choices[0].message.content or '{}')
        decision = parsed.get('decision')
        if decision not in {'AL','SAT','BEKLE'}:
            return Signal('ai', coin, 'UNAVAILABLE', 'AI çıktısı geçerli bir karar içermedi.', source=','.join(evidence['sources']))
        return Signal('ai', coin, decision, str(parsed.get('reason','Kaynaklı sosyal kanıt analiz edildi.')), source=','.join(evidence['sources']))
