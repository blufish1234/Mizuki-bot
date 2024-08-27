import requests
 
res = requests.get("https://api.nekosapi.com/v3/images/random/file")
res.raise_for_status()
print(res.url)