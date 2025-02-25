import requests
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import random
import time
import os
import threading
from colorama import Fore, Style, init
from shutil import get_terminal_size
from concurrent.futures import ThreadPoolExecutor
import json

# Inicializa colorama para compatibilidad con Windows
init()

CARACTERES = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}|;:',.<>/?"
TONALIDADES_VERDE = [
    Fore.LIGHTGREEN_EX,  # Verde claro
    Fore.GREEN,          # Verde medio
    Fore.LIGHTYELLOW_EX  # Verde amarillento
]

efecto_activo = True
proceso_cancelado = False  # Control de proceso cancelado
max_reintentos = 3  # Número máximo de reintentos

def efecto_visual_cuadro(visitados, en_proceso):
    """Muestra un efecto visual estilo decrypt dentro de un recuadro ajustado al 90% del tamaño de la terminal."""
    while efecto_activo:
        # Limpia la terminal
        os.system('cls' if os.name == 'nt' else 'clear')

        # Obtén el tamaño de la terminal
        ancho_terminal, alto_terminal = get_terminal_size()

        # Dimensiones del cuadro ajustado al 90% de la terminal
        ancho_cuadro = int(ancho_terminal * 0.9)
        alto_cuadro = int(alto_terminal * 0.9)

        # Coordenadas para centrar el cuadro
        margen_superior = (alto_terminal - alto_cuadro) // 2
        margen_lateral = (ancho_terminal - ancho_cuadro) // 2

        # Espaciado superior para centrar
        print("\n" * margen_superior, end="")

        # Mostrar encabezado centrado
        titulo = "Tecnología en proceso"
        print(" " * ((ancho_terminal - len(titulo)) // 2) + titulo)
        print(" " * margen_lateral + "+" + "-" * (ancho_cuadro - 2) + "+")  # Línea superior del cuadro

        # Dibujar el cuadro con líneas de texto aleatorio
        for _ in range(alto_cuadro - 2):  # Restamos 2 para dejar espacio para bordes superior e inferior
            texto_random = "".join(
                random.choice(TONALIDADES_VERDE) + random.choice(CARACTERES) + Style.RESET_ALL
                for _ in range(ancho_cuadro - 2)
            )
            print(" " * margen_lateral + "|" + texto_random + "|")

        print(" " * margen_lateral + "+" + "-" * (ancho_cuadro - 2) + "+")  # Línea inferior del cuadro
        
        # Mostrar lista de URLs y subdominios procesados
        print("\nSubdominios Visitados:")
        print(f"Visitas completas: {len(visitados)}")
        print(f"En proceso: {len(en_proceso)}")

        # Imprimir las URLs con estado
        for url in visitados:
            print(f"✔ {url}")
        for url in en_proceso:
            print(f". {url}")

        time.sleep(0.002)  # Ajustar la velocidad del efecto

def obtener_palabras_de_url(url):
    """Extrae palabras de una URL específica."""
    try:
        respuesta = requests.get(url)
        if respuesta.status_code == 200:
            soup = BeautifulSoup(respuesta.text, "html.parser")
            
            # Extraer texto y contenido de atributos importantes
            texto_principal = soup.get_text()
            palabras_meta = [meta.get("content", "") for meta in soup.find_all("meta") if meta.get("content")]
            palabras_alt = [img.get("alt", "") for img in soup.find_all("img") if img.get("alt")]
            palabras_title = [tag.get("title", "") for tag in soup.find_all(attrs={"title": True})]
            palabras_href = [a.get("href", "") for a in soup.find_all("a") if a.get("href")]

            # Combinar todas las palabras extraídas
            texto_completo = "\n".join([
                texto_principal,
                " ".join(palabras_meta),
                " ".join(palabras_alt),
                " ".join(palabras_title),
                " ".join(palabras_href)
            ])

            palabras = re.findall(r'\b[\w\-.@:/]+\b', texto_completo)
            return palabras
        else:
            print(f"Error al conectar con {url}, código de estado: {respuesta.status_code}")
            return []
    except requests.exceptions.RequestException as e:
        print(f"Excepción al intentar acceder a {url}: {e}")
        return []

def guardar_wordlist(parcial, archivo_salida="wordlist.txt"):
    """Guarda las palabras extraídas en un archivo, marcando el progreso."""
    total_palabras = len(parcial)
    
    # Guardar estado de la sesión
    with open("estado_sesion.json", "w", encoding="utf-8") as archivo_estado:
        json.dump({"visitados": list(parcial)}, archivo_estado)

    with open(archivo_salida, "w", encoding="utf-8") as archivo:
        for palabra in sorted(parcial):
            archivo.write(palabra + "\n")

    print(f"Wordlist guardada correctamente. Total de palabras: {total_palabras}")

def reintentar_conexion(url, max_reintentos=3):
    """Intenta conectar con la URL, con reintentos en caso de fallo."""
    reintentos = 0
    while reintentos < max_reintentos:
        try:
            respuesta = requests.get(url)
            if respuesta.status_code == 200:
                return respuesta
            else:
                print(f"Error en la respuesta para {url}: {respuesta.status_code}")
                reintentos += 1
                time.sleep(2)
        except requests.exceptions.RequestException as e:
            print(f"Error al intentar acceder a {url}: {e}")
            reintentos += 1
            time.sleep(2)
    return None

def procesar_url(url, palabras_totales):
    """Función para procesar cada URL y extraer palabras."""
    palabras = obtener_palabras_de_url(url)
    if palabras:
        palabras_totales.update(palabras)

def crawler_y_wordlist(base_url, archivo_salida="wordlist.txt", limite=50, recursivo=True):
    """Crea una wordlist recorriendo la página base y sus subdominios."""
    global efecto_activo, proceso_cancelado
    visitados = set()
    por_visitar = [base_url] if recursivo else []  # Cola de URLs si es recursivo
    palabras_totales = set()
    en_proceso = set()

    # Iniciar el hilo del efecto visual
    hilo_efecto = threading.Thread(target=efecto_visual_cuadro, args=(visitados, en_proceso))
    hilo_efecto.daemon = True  # Permitir que el hilo termine cuando el programa principal termine
    hilo_efecto.start()

    try:
        # Procesar la URL base
        print(f"Procesando: {base_url}")
        palabras_totales.update(obtener_palabras_de_url(base_url))
        visitados.add(base_url)

        with ThreadPoolExecutor(max_workers=5) as executor:
            while recursivo and len(visitados) < limite:
                url_actual = por_visitar.pop(0) if por_visitar else None

                if url_actual and url_actual not in visitados:
                    print(f"Visitando: {url_actual}")
                    en_proceso.add(url_actual)
                    executor.submit(procesar_url, url_actual, palabras_totales)

                    respuesta = reintentar_conexion(url_actual)
                    if respuesta:
                        soup = BeautifulSoup(respuesta.text, "html.parser")

                        for enlace in soup.find_all("a", href=True):
                            url_completa = urljoin(url_actual, enlace["href"])
                            dominio_base = urlparse(base_url).netloc
                            dominio_enlace = urlparse(url_completa).netloc

                            if dominio_base in dominio_enlace and url_completa not in visitados:
                                if '?' not in url_completa:  # Evitar enlaces con parámetros
                                    por_visitar.append(url_completa)

                    en_proceso.remove(url_actual)
                    visitados.add(url_actual)

                if proceso_cancelado:
                    # Guardar el estado antes de finalizar
                    guardar_wordlist(palabras_totales, archivo_salida)
                    print("\nProceso detenido. ¿Deseas continuar la sesión más tarde?")
                    continuar = input("¿Continuar la sesión en la próxima ejecución? (s/n): ").strip().lower()
                    if continuar == "s":
                        print("La sesión se guardará y podrá continuarla la próxima vez.")
                    break

        if not proceso_cancelado:
            # Guardar todas las palabras si el proceso termina sin interrupción
            guardar_wordlist(palabras_totales, archivo_salida)

        efecto_activo = False
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Wordlist generada exitosamente: {archivo_salida}")

    except Exception as e:
        efecto_activo = False
        print(f"Error durante la ejecución: {e}")


def solicitar_parametros():
    print("=== CRAWLER PARA GENERAR WORDLIST ===")

    # Solicitar URL base
    url_base = input("Ingresa la URL base (por defecto: https://www.ejemplo.com): ").strip()
    if not url_base:
        url_base = "https://www.ejemplo.com"

    # Solicitar límite de subdominios
    try:
        limite = int(input("Número de subdominios a visitar (por defecto: 50): ").strip())
    except ValueError:
        limite = 50

    # Solicitar nombre del archivo
    archivo_salida = input("Nombre del archivo de salida (por defecto: wordlist.txt): ").strip()
    if not archivo_salida:
        archivo_salida = "wordlist.txt"

    # Preguntar si es recursivo
    respuesta_recursivo = input("¿Recursivo? (s/n): ").strip().lower()
    recursivo = respuesta_recursivo == "s"

    return url_base, archivo_salida, limite, recursivo


if __name__ == "__main__":
    parametros = solicitar_parametros()
    crawler_y_wordlist(*parametros)

