import requests
import sqlite3
import time
import smtplib
from email.mime.text import MIMEText
import matplotlib.pyplot as plt

# OpenWeatherMap API and database settings
API_KEY = '39e34f4b08d78d04cceefadcef9d5f25'  # Insert your API key here
CITIES = ['Delhi', 'Mumbai', 'Chennai', 'Bangalore', 'Kolkata', 'Hyderabad']
INTERVAL = 20  # 10 seconds interval for testing purposes
DATABASE = 'weather_data.db'

# Temperature threshold for alerting
TEMP_THRESHOLD = 35.0  # in Celsius

# Set up SQLite database
def init_db():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS weather (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            city TEXT,
            temp REAL,
            feels_like REAL,
            humidity INTEGER,  -- Added humidity field
            main TEXT,
            dt INTEGER,
            date TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Add humidity column to the existing table if needed
def add_humidity_column():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    try:
        cursor.execute("ALTER TABLE weather ADD COLUMN humidity INTEGER")
        conn.commit()
        print("Humidity column added successfully!")
    except sqlite3.OperationalError:
        print("Column already exists or table has an issue.")
    finally:
        conn.close()

# Fetch weather data from OpenWeatherMap API
def fetch_weather(city):
    url = f'http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}'
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise error for HTTP issues
        data = response.json()
        weather = {
            'city': city,
            'temp': data['main']['temp'] - 273.15,  # Kelvin to Celsius
            'feels_like': data['main']['feels_like'] - 273.15,  # Kelvin to Celsius
            'humidity': data['main']['humidity'],  # Added humidity
            'main': data['weather'][0]['main'],
            'dt': data['dt'],
            'date': time.strftime('%Y-%m-%d', time.localtime(data['dt']))
        }
        return weather
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weather data for {city}: {e}")
        return None

# Store weather data in the database
def store_weather_data(weather):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO weather (city, temp, feels_like, humidity, main, dt, date)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (weather['city'], weather['temp'], weather['feels_like'], weather['humidity'], weather['main'], weather['dt'], weather['date']))
    conn.commit()
    conn.close()

# Generate daily weather summary (average, min, max temp, dominant condition, average humidity)
def generate_daily_summary():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    for city in CITIES:
        cursor.execute('''
            SELECT AVG(temp), MIN(temp), MAX(temp), AVG(humidity), main
            FROM weather WHERE city = ? AND date = ?
        ''', (city, time.strftime('%Y-%m-%d')))
        result = cursor.fetchone()
        print(f"\nSummary for {city} on {time.strftime('%Y-%m-%d')}:")
        print(f"Average Temperature: {result[0]:.2f} °C")
        print(f"Min Temperature: {result[1]:.2f} °C")
        print(f"Max Temperature: {result[2]:.2f} °C")
        print(f"Average Humidity: {result[3]:.2f}%")  # Added humidity to summary
        print(f"Dominant Condition: {result[4]}")
    
    conn.close()

# Alert if temperature exceeds threshold for two consecutive updates
def check_alerts(weather):
    if weather['temp'] > TEMP_THRESHOLD:
        print(f"ALERT! High temperature detected in {weather['city']}: {weather['temp']:.2f} °C")
        send_email_alert(weather)

# Send email alert (optional)
def send_email_alert(weather):
    sender = 'jeevaajayaswin@gmail.com'
    recipient = 'recipient_email@example.com'
    subject = f"Weather Alert: High Temperature in {weather['city']}"
    
    # Build the email body with proper formatting
    body = (f"Alert! The temperature in {weather['city']} has exceeded {TEMP_THRESHOLD}°C.\n\n"
            f"Current Temperature: {weather['temp']:.2f} °C\n"
            f"Feels Like: {weather['feels_like']:.2f} °C\n"
            f"Humidity: {weather['humidity']}%\n"
            f"Condition: {weather['main']}")
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = recipient

    try:
        with smtplib.SMTP('smtp.example.com', 587) as server:  # Replace with the correct SMTP server
            server.starttls()
            server.login(sender, 'your_email_password')  # Use your email password
            server.sendmail(sender, recipient, msg.as_string())
        print("Alert email sent successfully!")
    except Exception as e:
        print(f"Failed to send email alert: {e}")

# Visualization of daily weather summary
def visualize_weather_data():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    
    for city in CITIES:
        cursor.execute('''
            SELECT date, AVG(temp), AVG(humidity)
            FROM weather
            WHERE city = ?
            GROUP BY date
            ORDER BY date
        ''', (city,))
        data = cursor.fetchall()
        dates = [row[0] for row in data]
        avg_temps = [row[1] for row in data]
        avg_humidity = [row[2] for row in data]  # Added humidity to visualization
        
        plt.plot(dates, avg_temps, label=f'{city} Temp')
        plt.plot(dates, avg_humidity, label=f'{city} Humidity', linestyle='--')  # Humidity plot
    
    plt.title('Average Daily Temperature and Humidity for Cities')
    plt.xlabel('Date')
    plt.ylabel('Temperature (°C) / Humidity (%)')
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
    
    conn.close()

# Main function to continuously fetch weather data and process it
def main():
    init_db()  # Initializes the database 
    add_humidity_column()  # Adds humidity column if it doesn't exist
    
    while True:
        for city in CITIES:
            weather = fetch_weather(city)
            if weather:
                store_weather_data(weather)
                check_alerts(weather)
        
        # Generate summary at the end of each day
        if time.strftime('%H:%M') == '23:59':
            generate_daily_summary()
        
        # Sleep for the configured interval (now 20 seconds for testing purposes)
        time.sleep(INTERVAL)

if __name__ == '__main__':
    main()
