import random
from pytrends.request import TrendReq
from src.utils.logger import log


def get_google_trends(limit=10):
    results = []
    try:
        pt = TrendReq(hl='en-US', tz=330, timeout=(10, 25),
                      retries=2, backoff_factor=0.5)
        for region in ['united_states', 'india', 'united_kingdom']:
            try:
                df = pt.trending_searches(pn=region)
                if df is not None and not df.empty:
                    for topic in df[0].tolist()[:4]:
                        results.append({
                            'topic':  str(topic).strip(),
                            'source': f'google_trends_{region}',
                            'score':  random.randint(75, 100),
                        })
            except Exception as e:
                log.debug(f"Google Trends [{region}]: {e}")
        log.info(f"Google Trends: {len(results)} topics")
    except Exception as e:
        log.warning(f"Google Trends failed: {e}")
    return results[:limit]
