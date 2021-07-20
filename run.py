from crc import app

if __name__ == "__main__":
    flask_port = app.config['FLASK_PORT']
    app.run(host='0.0.0.0', port=flask_port)
