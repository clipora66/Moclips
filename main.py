import os
import uuid
import shutil
import zipfile
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg

app = FastAPI(title="MOCLIPS")

BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "outputs"
OUTPUT_DIR.mkdir(exist_ok=True)

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()


HTML = """
<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>MOCLIPS</title>
<style>
body {
    margin: 0;
    background: #080808;
    color: white;
    font-family: Arial, sans-serif;
    text-align: center;
}
.container {
    max-width: 600px;
    margin: 70px auto;
    padding: 25px;
}
h1 {
    color: #00ff66;
    font-size: 45px;
    letter-spacing: 4px;
}
p {
    color: #bbb;
}
.box {
    background: #151515;
    padding: 25px;
    border-radius: 15px;
    margin-top: 30px;
}
input {
    margin: 20px 0;
    max-width: 100%;
}
button {
    background: #00ff66;
    color: black;
    border: none;
    padding: 17px 30px;
    border-radius: 10px;
    font-weight: bold;
    font-size: 17px;
    cursor: pointer;
}
button:disabled {
    opacity: 0.5;
}
#mensaje {
    margin-top: 25px;
    color: #00ff66;
}
</style>
</head>
<body>
<div class="container">
    <h1>MOCLIPS</h1>
    <p>Tu plataforma de generación automática de clips.</p>
    <p>Convierte tus videos en clips fácilmente.</p>

    <div class="box">
        <h2>CREAR CLIPS</h2>
        <input type="file" id="video" accept="video/*">
        <br>
        <button id="boton" onclick="generarClip()">
            GENERAR CLIP
        </button>
        <div id="mensaje"></div>
    </div>
</div>

<script>
async function generarClip() {
    const archivo = document.getElementById("video").files[0];
    const boton = document.getElementById("boton");
    const mensaje = document.getElementById("mensaje");

    if (!archivo) {
        mensaje.innerText = "Selecciona un video primero.";
        return;
    }

    boton.disabled = true;
    mensaje.innerText = "MOCLIPS está procesando tu video...";

    const datos = new FormData();
    datos.append("video", archivo);

    try {
        const respuesta = await fetch("/generar", {
            method: "POST",
            body: datos
        });

        if (!respuesta.ok) {
            const error = await respuesta.json();
            throw new Error(error.detail || "Error al procesar.");
        }

        const archivoZip = await respuesta.blob();
        const url = URL.createObjectURL(archivoZip);

        const enlace = document.createElement("a");
        enlace.href = url;
        enlace.download = "MOCLIPS_resultados.zip";
        enlace.click();

        URL.revokeObjectURL(url);

        mensaje.innerText = "¡Tus clips están listos!";
    } catch (error) {
        mensaje.innerText = error.message;
    } finally {
        boton.disabled = false;
    }
}
</script>
</body>
</html>
"""


def crear_marca_agua(ruta):
    imagen = Image.new("RGBA", (500, 90), (0, 0, 0, 0))
    dibujo = ImageDraw.Draw(imagen)

    try:
        fuente = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
    except OSError:
        fuente = ImageFont.load_default()

    dibujo.text(
        (10, 10),
        "MOCLIPS",
        font=fuente,
        fill=(0, 255, 102, 210)
    )

    imagen.save(ruta)


@app.get("/", response_class=HTMLResponse)
def inicio():
    return HTML


@app.post("/generar")
async def generar(video: UploadFile = File(...)):

    extension = Path(video.filename or "").suffix.lower()

    extensiones = {
        ".mp4", ".mov", ".mkv", ".avi", ".webm"
    }

    if extension not in extensiones:
        raise HTTPException(
            status_code=400,
            detail="Formato de video no compatible."
        )

    identificador = uuid.uuid4().hex

    with tempfile.TemporaryDirectory() as temporal:

        carpeta = Path(temporal)

        entrada = carpeta / f"video{extension}"
        marca = carpeta / "marca.png"
        salida = carpeta / "clip_%03d.mp4"

        zip_path = OUTPUT_DIR / f"{identificador}.zip"

        try:
            tamanio = 0

            with open(entrada, "wb") as archivo:
                while True:
                    bloque = await video.read(1024 * 1024)

                    if not bloque:
                        break

                    tamanio += len(bloque)

                    if tamanio > 500 * 1024 * 1024:
                        raise HTTPException(
                            status_code=413,
                            detail="El video supera los 500 MB."
                        )

                    archivo.write(bloque)

            await video.close()

            if tamanio == 0:
                raise HTTPException(
                    status_code=400,
                    detail="El archivo está vacío."
                )

            crear_marca_agua(marca)

            comando = [
                FFMPEG,
                "-y",
                "-i", str(entrada),
                "-loop", "1",
                "-i", str(marca),
                "-filter_complex",
                "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2[v];"
                "[v][1:v]overlay=W-w-25:H-h-25:format=auto",
                "-map", "0:a?",
                "-c:v", "libx264",
                "-preset", "ultrafast",
                "-crf", "23",
                "-c:a", "aac",
                "-b:a", "128k",
                "-f", "segment",
                "-segment_time", "30",
                "-reset_timestamps", "1",
                str(salida)
            ]

            resultado = subprocess.run(
                comando,
                capture_output=True,
                text=True,
                timeout=1800
            )

            if resultado.returncode != 0:
                raise RuntimeError(resultado.stderr[-2000:])

            clips = sorted(carpeta.glob("clip_*.mp4"))

            if not clips:
                raise RuntimeError("No se pudieron generar los clips.")

            with zipfile.ZipFile(
                zip_path,
                "w",
                zipfile.ZIP_DEFLATED
            ) as archivo_zip:

                for clip in clips:
                    archivo_zip.write(
                        clip,
                        arcname=clip.name
                    )

            return FileResponse(
                zip_path,
                media_type="application/zip",
                filename="MOCLIPS_resultados.zip"
            )

        except HTTPException:
            raise

        except subprocess.TimeoutExpired:
            raise HTTPException(
                status_code=504,
                detail="El procesamiento tardó demasiado."
            )

        except Exception as error:
            raise HTTPException(
                status_code=500,
                detail=f"Error procesando el video: {str(error)[:500]}"
            )


@app.get("/health")
def health():
    return {"status": "ok"}
