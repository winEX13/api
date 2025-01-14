import asyncio
from pyppeteer import launch
from pyppeteer_stealth import stealth
from pyppeteer.errors import TimeoutError
from fastapi import FastAPI, HTTPException
import json
from typing import Optional
import re
import datetime

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
        schedule = [(k, v.replace('\xa0', ' '))
            for k, v in zip(schedule[::2], schedule[1::2]) if re.fullmatch(r'\d{2}:\d{2}', v)
        ]
        def suffix(number, singular, few, many):
            number = abs(number) % 100
            if 11 <= number <= 19: return many
            last_digit = number % 10
            if last_digit == 1: return singular
            elif 2 <= last_digit <= 4: return few
            else: return many
        def left(duration):
            days, seconds = duration.days, duration.seconds
            hours = days * 24 + seconds // 3600
            minutes = (seconds % 3600) // 60
            seconds = seconds % 60
            return duration.total_seconds(), f"Осталось {minutes} {suffix(minutes, 'минута', 'минуты', 'минут')} и {seconds} {suffix(seconds, 'секунда', 'секунды', 'секунд')}"
        now = datetime.datetime.now()
        return [{'name': k, 'time': v} | dict(zip(('total', 'left'), left(datetime.datetime.strptime(v, '%H:%M').replace(year=now.year, month=now.month, day=now.day) - now))) for k, v in schedule]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await page.close()

@app.get('/')
async def scrape_endpoint():
    url = 'https://yandex.ru/maps/213/moscow/stops/stop__9645057/?ll=37.742975%2C55.651185&tab=timetable&z=10'
    data = await scrape_data(url)
    await stop_browser()
    return data
