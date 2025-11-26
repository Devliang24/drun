import requests
import json

url = "https://httpbin.org/post"

payload = json.dumps({
  "user_name": "${fake_name()}",
  "user_email": "${fake_email()}",
  "user_address": "${fake_address()}",
  "short_bio": "${fake_text(20)}",
  "ip": "${fake_ipv4()}",
  "company": "${fake_company()}"
})
headers = {}

response = requests.request("POST", url, headers=headers, data=payload)

print(response.text)