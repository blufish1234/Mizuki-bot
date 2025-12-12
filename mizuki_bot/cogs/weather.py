import discord
from discord.ext import commands
from discord import app_commands
import weatherapi
from weatherapi.rest import ApiException
from datetime import datetime
import os

class Weather(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.WeatherAPIKEY = os.getenv("WEATHERAPI_API_KEY")

    # 天氣查詢
    @app_commands.command(
        name="查詢天氣", description=("使用 WeatherAPI.com 查詢指定地點的天氣")
    )
    @app_commands.rename(region="地區")
    @app_commands.describe(region="請輸入地區的英文名稱")
    async def rtweather(self, interaction: discord.Interaction, region: str):
        await interaction.response.defer()

        configuration = weatherapi.Configuration()
        configuration.api_key["key"] = self.WeatherAPIKEY

        api_instance = weatherapi.APIsApi(weatherapi.ApiClient(configuration))
        lang = "zh_tw"

        try:
            api_response = api_instance.realtime_weather(region, lang=lang)
            location = api_response.get("location", {}).get("name")
            region = api_response.get("location", {}).get("region")
            country = api_response.get("location", {}).get("country")
            weather_icon = api_response.get("current", {}).get("condition", {}).get("icon")
            weather = api_response.get("current", {}).get("condition", {}).get("text")
            temperature = api_response.get("current", {}).get("temp_c")
            lastupdated = api_response.get("current", {}).get("last_updated_epoch")
            windspeed = api_response.get("current", {}).get("wind_kph")
            gustspeed = api_response.get("current", {}).get("gust_kph")
            winddegree = api_response.get("current", {}).get("wind_degree")
            winddir = api_response.get("current", {}).get("wind_dir")
            pressure = api_response.get("current", {}).get("pressure_mb") * 0.1
            precipitation = api_response.get("current", {}).get("precip_mm")
            humidity = api_response.get("current", {}).get("humidity")
            cloudcover = api_response.get("current", {}).get("cloud")
            feelslike = api_response.get("current", {}).get("feelslike_c")
            dewpoint = api_response.get("current", {}).get("dewpoint_c")
            visibility = api_response.get("current", {}).get("vis_km")
            uvindex = api_response.get("current", {}).get("uv")

            embed = discord.Embed(
                title=f"{location}, {region}, {country}的實時天氣",
                color=discord.Color(int("2A324B", 16)),
                timestamp=datetime.fromtimestamp(lastupdated),
            )
            embed.set_thumbnail(url=f"https:{weather_icon}")
            embed.add_field(name="天氣狀況", value=weather)
            embed.add_field(name="溫度", value=f"{temperature}°C")
            embed.add_field(
                name="風向&風速",
                value=f"{windspeed}km/h {winddegree}° {winddir}, 陣風{gustspeed}km/h",
            )
            embed.add_field(name="大氣壓強", value=f"{round(pressure, 2)}KPa")
            embed.add_field(name="降雨/降雪量", value=f"{precipitation}mm")
            embed.add_field(name="相對濕度", value=f"{humidity}%")
            embed.add_field(name="雲層覆蓋度", value=f"{cloudcover}%")
            embed.add_field(name="體感溫度", value=f"{feelslike}°C")
            embed.add_field(name="露點溫度", value=f"{dewpoint}°C")
            embed.add_field(name="能見度", value=f"{visibility}km")
            embed.add_field(name="紫外線指數", value=f"{uvindex}")
            embed.set_author(name="WeatherAPI.com")
            await interaction.followup.send(embed=embed)
        except ApiException as e:
            await interaction.followup.send(
                "調用API時出錯 Api->realtime_weather: %s\n" % e, ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(Weather(bot))
