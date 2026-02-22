# architectureOfComputer
# Microservices

## Setup

```bash
pip install flask requests protobuf
```

## Running

Open **three separate terminals**:

```bash
# Terminal 1
python3 logging-service/main.py

# Terminal 2
python3 messages-service/main.py

# Terminal 3
python3 facade-service/main.py
```

## Usage

### POST — Send a message
```bash
curl -X POST http://localhost:8000/ \
  -H "Content-Type: application/json" \
  -d '{"msg": "Hello, microservices!"}'
```

### GET — Retrieve all messages
```bash
curl http://localhost:8000/
```
