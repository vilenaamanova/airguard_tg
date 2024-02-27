import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import requests
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO)

open_weather_token = "c2cfce186c6cdc990ca483ab241a0d1e"
tg_bot_token = "6703680303:AAFAaRXi_Dkcxp180WHrCTP-gMIzD7ehG1I"

bot = Bot(token=tg_bot_token)
dp = Dispatcher(bot, storage=MemoryStorage())

keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
buttons = [KeyboardButton(text=area) for area in ["СеверныйАО", "ВосточныйАО", "ЗападныйАО", "ЗеленоградскийАО",
                                                  "СевероВосточныйАО", "СевероЗападныйАО", "ЦентральныйАО",
                                                  "ЮгоВосточныйАО",
                                                  "ЮгоЗападныйАО", "ЮжныйАО"]]
keyboard.add(*buttons)

@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Выбери свой округ:", reply_markup=keyboard)

# Обработчик ответов на кнопки выбора округа
@dp.message_handler(lambda message: message.text in ["СеверныйАО", "ВосточныйАО", "ЗападныйАО", "ЗеленоградскийАО",
                                                     "СевероВосточныйАО", "СевероЗападныйАО", "ЦентральныйАО",
                                                     "ЮгоВосточныйАО",
                                                     "ЮгоЗападныйАО", "ЮжныйАО"])
async def choose_area(message: types.Message, state: FSMContext):
    area = message.text
    await state.update_data(chosen_area=area)
    await message.answer(f"Вы выбрали округ {area}. Теперь выберите действие:", reply_markup=keyboard_weather_and_air_quality)

keyboard_weather_and_air_quality = ReplyKeyboardMarkup(resize_keyboard=True)
weather_and_air_quality_buttons = [
    KeyboardButton(text="Узнать погоду"),
    KeyboardButton(text="Узнать качество воздуха")
]
keyboard_weather_and_air_quality.add(*weather_and_air_quality_buttons)


@dp.message_handler(lambda message: message.text == "Узнать погоду")
async def get_weather(message: types.Message, state: FSMContext):
    user_data = await state.get_data()  # получаем данные из контекста FSM
    area = user_data['chosen_area']  # извлекаем выбранный округ
    print(area)
    city = "Москва"
    weather_data = get_weather_data(city)
    aqi = extract_aqi_from_api(get_api_url(area))

    await message.answer(f"Текущая погода в городе {city}:\n"
                         f"Температура: {weather_data['temp']}°C\n"
                         f"Ощущается как: {weather_data['feels_like']}°C\n"
                         f"Давление: {weather_data['pressure']} hPa\n"
                         f"Влажность: {weather_data['humidity']}%\n"
                         f"Ветер: {weather_data['wind']['speed']} м/с, направление {weather_data['wind']['deg']}°\n"
                         f"AQI (Индекс качества воздуха): {aqi}")


def get_api_url(area):
    folder_path = f"../../{area}"

    try:
        file_name = next(file for file in os.listdir(folder_path) if file.endswith("-API"))
        file_path = os.path.join(folder_path, file_name)

        with open(file_path, 'r') as file:
            api_url = file.read().strip()
            return api_url
    except (FileNotFoundError, StopIteration):
        return "Данные об API не найдены"


def extract_aqi_from_api(api_url):
    try:
        response = requests.get(api_url)
        data = response.json()
        aqi_value = data["data"]["aqi"]
        return aqi_value
    except (requests.RequestException, ValueError):
        return "Ошибка при получении данных из API"


def get_weather_data(city):
    url = f"http://api.openweathermap.org/data/2.5/weather?q=Moscow&appid={open_weather_token}&units=metric"
    response = requests.get(url)
    data = response.json()

    weather_data = {
        "temp": data["main"]["temp"],
        "feels_like": data["main"]["feels_like"],
        "pressure": data["main"]["pressure"],
        "humidity": data["main"]["humidity"],
        "wind": {
            "speed": data["wind"]["speed"],
            "deg": data["wind"]["deg"]
        }
    }

    return weather_data

@dp.message_handler(lambda message: message.text == "Узнать качество воздуха")
async def get_air_quality(message: types.Message, state: FSMContext):
    data = await state.get_data()
    area = data.get("chosen_area", "неизвестный округ")

    api_url = get_api_url(area)
    air_quality_data = get_air_quality_data(api_url)
    recommendations = get_health_recommendations(air_quality_data)

    await message.answer(f"Данные о качестве воздуха в {area}:\n"
                         f"PM2.5: {air_quality_data['pm25']} µg/m³\n"
                         f"PM10: {air_quality_data['pm10']} µg/m³\n"
                         f"AQI (Индекс качества воздуха): {air_quality_data['aqi']}\n"
                         f"\nРекомендации по охране здоровья:\n\n{recommendations}",
                         reply_markup=keyboard_weather_and_air_quality)

def get_air_quality_data(api_url):
    try:
        response = requests.get(api_url)
        data = response.json()

        if "data" in data and "iaqi" in data["data"]:
            iaqi_data = data["data"]["iaqi"]
            air_quality_data = {
                "pm25": iaqi_data.get("pm25", {}).get("v", "Недоступно"),
                "pm10": iaqi_data.get("pm10", {}).get("v", "Недоступно"),
                "aqi": data["data"]["aqi"]
            }
            return air_quality_data
        else:
            return {"pm25": "Недоступно", "pm10": "Недоступно", "aqi": "Недоступно"}
    except (requests.RequestException, ValueError):
        return {"pm25": "Недоступно", "pm10": "Недоступно", "aqi": "Недоступно"}


def get_health_recommendations(air_quality_data):
    pm25 = air_quality_data["pm25"]
    pm10 = air_quality_data["pm10"]
    aqi = air_quality_data["aqi"]

    recommendations = ""

    if pm25 != "Недоступно" and pm10 != "Недоступно" and aqi != "Недоступно":
        # if aqi >= 0 & aqi <= 50:
        #     recommendations += ("Воздух качественный, без влияния на здоровье.\nРекомендации: Нет особых ограничений. "
        #                         "Наслаждайтесь активностью на открытом воздухе.\n")
        # elif aqi > 50 & aqi <= 100:
        #     recommendations += ("Качество воздуха приемлемое; однако, для чувствительных групп могут возникнуть "
        #                         "небольшие проблемы.\nРекомендации: Люди, страдающие заболеваниями дыхательных путей, "
        #                         "дети и пожилые, могут ограничить продолжительность интенсивных физических упражнений "
        #                         "на улице.\n")
        # elif aqi > 100 & aqi <= 150:
        #     recommendations += ("Качество воздуха: (Нездоровое для чувствительных групп):\nЗдоровье: Люди, входящие в "
        #                         "чувствительные группы (дети, пожилые, люди с заболеваниями дыхательных путей), "
        #                         "могут столкнуться с трудностями.\nРекомендации: Рекомендуется членам чувствительных "
        #                         "групп рассмотреть возможность ограничения времени, проведенного на улице. Однако все "
        #                         "остальные могут продолжать свои обычные активности.\n")
        # elif aqi > 150 & aqi <= 200:
        #     recommendations += ("Все группы населения могут начать испытывать негативные эффекты на здоровье.\n"
        #                         "Рекомендации: Все люди, особенно члены чувствительных групп, должны ограничивать "
        #                         "физические активности на улице и принимать предосторожности, такие как ношение масок.\n")
        # elif aqi > 200 & aqi <= 300:
        #     recommendations += ("Все группы населения могут испытывать более серьезные эффекты на здоровье.\n"
        #                         "Рекомендации: Ограничение физических активностей на улице для всех. Люди с "
        #                         "заболеваниями дыхательных путей должны избегать пребывания на улице, "
        #                         "если это возможно.\n")
        # elif aqi > 300:
        #     recommendations += ("Чрезвычайно высокий уровень загрязнения, представляющий серьезную угрозу "
        #                         "здоровью.\nРекомендации: Все граждане должны минимизировать время, проведенное на "
        #                         "улице. Люди с хроническими заболеваниями должны найти убежище в закрытых помещениях.\n")
        if 0 <= pm25 <= 12:
            recommendations += ("Воздух чистый, без влияния на здоровье.\n\nРекомендации: Нет особых ограничений. "
                                "Можно наслаждаться активностью на открытом воздухе.\n")
        elif 13 <= pm25 <= 35:
            recommendations += (f"Качество воздуха приемлемое; однако, для чувствительных групп могут возникнуть "
                                "небольшие проблемы.\n\nРекомендации: Люди, страдающие заболеваниями дыхательных путей, "
                                "дети и пожилые, могут ограничить продолжительность интенсивных физических упражнений "
                                "на улице.\n")
        elif 36 <= pm25 <= 55:
            recommendations += ("Качество воздуха умеренное, некоторое воздействие на здоровье.\n\nРекомендации: "
                                "Людям с"
                                "хроническими заболеваниями и чувствительными группами следует рассмотреть ограничение "
                                "времени, проведенного на улице.\n")
        elif 56 <= pm25 <= 150:
            recommendations += ("Чувствительные группы могут испытывать более серьезные эффекты на здоровье.\n\n"
                                "Рекомендации: Члены чувствительных групп должны ограничивать физические активности на "
                                "улице и рассмотреть использование масок.\n")
        elif 151 <= pm25 <= 250:
            recommendations += ("Все группы населения могут начать испытывать негативные эффекты на здоровье.\n"
                                "Рекомендации: Ограничение физических активностей на улице для всех. Люди с "
                                "хроническими заболеваниями должны избегать пребывания на улице, если это возможно.\n")
        elif pm25 > 250:
            recommendations += ("Экстремально высокий уровень загрязнения, представляющий серьезную угрозу "
                                "здоровью.\nРекомендации: Все граждане должны минимизировать время, проведенное на "
                                "улице. Люди с хроническими заболеваниями должны находиться в закрытых помещениях.\n")

    return recommendations


@dp.message_handler(commands=['start'])
async def start(message: types.Message):
    await message.answer("Привет! Выбери свой округ:", reply_markup=keyboard)


if __name__ == '__main__':
    from aiogram import executor

    executor.start_polling(dp, skip_updates=True)
