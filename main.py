from fastapi import FastAPI

app = FastAPI(title="MOCLIPS")

@app.get("/")
def inicio():
    return {
        "mensaje": "MOCLIPS está funcionando correctamente",
        "estado": "online"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
