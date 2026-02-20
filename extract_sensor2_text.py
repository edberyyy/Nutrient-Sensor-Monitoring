from monitor import get_dashboard_data, DASHBOARDS

url = DASHBOARDS['Sensor 2']
text = get_dashboard_data(url, 'Sensor 2')
with open('sensor2_text.txt', 'w', encoding='utf-8') as f:
    f.write(text)
print('Saved to sensor2_text.txt')
print('Text length:', len(text))
