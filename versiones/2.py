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

# Inicializa colorama para compatibilidad con Windows
init()

CARACTERES = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()-_=+[]{}|;:',.<>?/"
TONALIDADES_VERDE = [
    Fore.LIGHTGREEN_EX,  # Verde claro
    Fore.GREEN,          # Verde medio
    Fore.LIGHTYELLOW_EX  # Verde amarillento
]

efecto_activo = True
proceso_cancelado = False  # Control de proceso cancelado

# Función para manejar la interrupción del proceso
def detener_proceso():
    """Función para manejar la interrupción del proceso por parte del usuario."""
    global proceso_cancelado
    while True:
        comando = input("\n¿Deseas detener el proceso? (s para detener, n para continuar): ").strip().lower()
        if comando == "s":
            proceso_cancelado = True
            break
        elif comando == "n":
            break


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

        time.sleep(0.1)  # Ajustar la velocidad del efecto


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

    with open(archivo_salida, "w", encoding="utf-8") as archivo:
        for palabra in sorted(parcial):
            archivo.write(palabra + "\n")

    print(f"Wordlist guardada correctamente. Total de palabras: {total_palabras}")


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

    # Iniciar hilo para manejar la interrupción del usuario
    hilo_detener = threading.Thread(target=detener_proceso)
    hilo_detener.daemon = True  # Permitir que el hilo termine cuando el programa principal termine
    hilo_detener.start()

    try:
        # Procesar la URL base
        print(f"Procesando: {base_url}")
        palabras_totales.update(obtener_palabras_de_url(base_url))
        visitados.add(base_url)

        # Si es recursivo, continuar con los subdominios
        while recursivo and por_visitar and len(visitados) < limite:
            url_actual = por_visitar.pop(0)

            if url_actual not in visitados:
                print(f"Visitando: {url_actual}")
                en_proceso.add(url_actual)
                palabras_totales.update(obtener_palabras_de_url(url_actual))

                try:
                    respuesta = requests.get(url_actual)
                    if respuesta.status_code == 200:
                        print(f"{url_actual} - Conexión exitosa: {respuesta.status_code}")
                    else:
                        print(f"{url_actual} - Error: {respuesta.status_code}")
                    
                    soup = BeautifulSoup(respuesta.text, "html.parser")

                    for enlace in soup.find_all("a", href=True):
                        url_completa = urljoin(url_actual, enlace["href"])
                        dominio_base = urlparse(base_url).netloc
                        dominio_enlace = urlparse(url_completa).netloc

                        if dominio_base in dominio_enlace and url_completa not in visitados:
                            por_visitar.append(url_completa)

                    en_proceso.remove(url_actual)
                    visitados.add(url_actual)

                except requests.exceptions.RequestException:
                    continue

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
        hilo_detener.join()  # Asegurarse de que el hilo de interrupción termine
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"Wordlist generada exitosamente: {archivo_salida}")

    except Exception as e:
        efecto_activo = False
        hilo_detener.join()
        print(f"Error durante la ejecución: {e}")


# Solicitar parámetros al usuario
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

# Llamar a la función principal
if __name__ == "__main__":
    parametros = solicitar_parametros()
    crawler_y_wordlist(*parametros)
