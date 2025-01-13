import asyncio
from pyppeteer import launch
from pyppeteer_stealth import stealth
from pyppeteer.errors import TimeoutError
from fastapi import FastAPI, HTTPException
import json
from typing import Optional

app = FastAPI()

browser = None

async def start_browser():
    global browser
    if not browser:
        browser = await launch({
            'headless': True,
            'autoClose': True,
            'args': [
                '--lang=ru',
                '--no-sandbox',
                '--disable-setuid-sandbox',
            ]
        })

async def stop_browser():
    global browser
    if browser:
        await browser.close()
        browser = None

async def get_element(page, xpath: str, properties):
    try:
        await page.waitForXPath(xpath, timeout=10 * 1000)
    except TimeoutError:
        return ['']
    else:
        data = []
        for element in await page.xpath(xpath):
            data.append(
                [await (await element.getProperty(property)).jsonValue() for property in properties]
                if isinstance(properties, list)
                else await (await element.getProperty(properties)).jsonValue()
            )
        return data

async def scrape_data(url: str):
    global browser
    if not browser:
        await start_browser()

    page = await browser.newPage()
    await stealth(page)

    try:
        await page.goto(url, timeout=0)
        await page.waitFor(1000)  # Дождаться полной загрузки страницы
        schedule = await get_element(
            page,
            "//div[@class='masstransit-timetable-view__transports']/li[@class='masstransit-vehicle-snippet-view _clickable _type_bus']/div[@class='masstransit-vehicle-snippet-view__row']/div[contains(@class, 'masstransit-vehicle-snippet-view__info') or contains(@class, 'masstransit-vehicle-snippet-view__prognoses')]//*[contains(@class, 'masstransit-vehicle-snippet-view__main-text') or contains(@class, 'masstransit-timetable-view__time')]",
            'textContent'
        )
        return {
            f"[{i}] {k}": v.replace('\xa0', ' ')
            for i, (k, v) in enumerate(zip(schedule[::2], schedule[1::2]), 1)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await page.close()

@app.get('/')
async def scrape_endpoint(url: Optional[str] = None):
    url = 'https://yandex.ru/maps/213/moscow/stops/stop__9645057/?ll=37.742975%2C55.651185&tab=timetable&z=10'
    data = await scrape_data(url)
    await stop_browser()
    return data

# async def get(page):
#     await page.reload()
#     return await getElement(page, "//div[@class='masstransit-timetable-view__transports']/li[@class='masstransit-vehicle-snippet-view _clickable _type_bus']/div[@class='masstransit-vehicle-snippet-view__row']/div[contains(@class, 'masstransit-vehicle-snippet-view__info') or contains(@class, 'masstransit-vehicle-snippet-view__prognoses')]//*[contains(@class, 'masstransit-vehicle-snippet-view__main-text') or contains(@class, 'masstransit-timetable-view__time')]", 'textContent')

# async def main(url):
#     browser = await connect()
    
#     page = await browser.newPage()
#     await stealth(page)
    
#     response = await page.goto(url, timeout=0)
#     await page.waitFor(1000)
    
#     schedule = await get(page)
    
#     # await page.reload()
    
#     # schedule = await getElement(page, "//div[@class='masstransit-timetable-view__transports']/li[@class='masstransit-vehicle-snippet-view _clickable _type_bus']/div[@class='masstransit-vehicle-snippet-view__row']/div[contains(@class, 'masstransit-vehicle-snippet-view__info') or contains(@class, 'masstransit-vehicle-snippet-view__prognoses')]//*[contains(@class, 'masstransit-vehicle-snippet-view__main-text') or contains(@class, 'masstransit-timetable-view__time')]", 'textContent')
    
#     await browser.close()
    
#     return json.dumps({f'[{i}] {k}': v.replace('\xa0', ' ') for i, (k, v) in enumerate(zip(schedule[::2], schedule[1::2]), 1)})
    
# if __name__ == '__main__':
#     url = 'https://yandex.ru/maps/213/moscow/stops/stop__9645057/?ll=37.742975%2C55.651185&tab=timetable&z=10'
#     router.add_api_route('/', endpoint=get)
#     app.include_router(router)
#     asyncio.run(main(url))
