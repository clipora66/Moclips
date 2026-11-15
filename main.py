from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="MOCLIPS")


@app.get("/", response_class=HTMLResponse)
def inicio():
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>MOCLIPS</title>

        <style>
            body {
                margin: 0;
                padding: 0;
                background: #080808;
                color: white;
                font-family: Arial, sans-serif;
                text-align: center;
            }

            .container {
                padding: 80px 20px;
            }

            h1 {
                font-size: 45px;
                color: #00ff66;
                letter-spacing: 4px;
            }

            p {
                color: #bbbbbb;
                font-size: 17px;
            }

            button {
                background: #00ff66;
                color: black;
                border: none;
                padding: 18px 35px;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
                cursor: pointer;
                margin-top: 30px;
            }

            button:hover {
                background: #00cc55;
            }

            #mensaje {
                margin-top: 30px;
                color: #00ff66;
                font-size: 18px;
            }
        </style>
    </head>

    <body>

        <div class="container">

            <h1>MOCLIPS</h1>

            <p>Tu plataforma de generación automática de clips.</p>

            <p>Convierte tus videos en clips fácilmente.</p>

            <button onclick="generarClip()">
                GENERAR CLIP
            </button>

            <div id="mensaje"></div>

        </div>

        <script>
            function generarClip() {
                document.getElementById("mensaje").innerHTML =
                "¡MOCLIPS está listo! Generador en preparación.";
            }
        </script>

    </body>
    </html>
    """


@app.get("/health")
def health():
    return {"status": "ok"}
