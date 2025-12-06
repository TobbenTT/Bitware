# 🛒 Bitware - E-commerce de Hardware con Inteligencia Artificial 🖥️

![PHP](https://img.shields.io/badge/PHP-8.0+-777BB4?style=for-the-badge&logo=php&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0+-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.95+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-ES6+-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.0+-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white)

👋 **¡Bienvenido al repositorio de Bitware!**

**Bitware** es una plataforma de comercio electrónico integral diseñada para modernizar la venta de componentes tecnológicos. A diferencia de un e-commerce tradicional, esta solución integra **Inteligencia Artificial (IA)** y **Minería de Datos** para optimizar tanto la experiencia del usuario como la gestión administrativa.

El sistema implementa una **Arquitectura Multicapa** que conecta un backend robusto en **PHP/MySQL** con microservicios de IA desarrollados en **Python (FastAPI/Flask)**, permitiendo funcionalidades avanzadas como recomendaciones personalizadas y predicción de stock.

→ ¡Dale una ⭐ a este repositorio si te gusta el proyecto!

---

## ✨ Características Principales

### 🤖 IA y Microservicios (Python)
* **Motor de Recomendaciones:** Sistema inteligente que analiza el comportamiento del usuario para sugerir productos personalizados en tiempo real.
* **Chatbot de Asistencia 24/7:** Asistente virtual basado en NLP para resolver consultas frecuentes de clientes automáticamente.
* **Predicción de Stock:** Módulo de minería de datos que analiza el historial de ventas para predecir la demanda futura y evitar quiebres de inventario.

### 🛠️ Backend y Gestión (PHP & MySQL)
* **Gestión Integral (CRUD):** Administración completa de usuarios, catálogo de productos, pedidos e inventario.
* **Panel Administrativo:** Dashboard visual para el control de métricas clave y toma de decisiones.
* **Arquitectura Segura:** Implementación de estándares **OWASP Top 10**, cifrado de contraseñas con **bcrypt** y seguridad HTTPS (SSL/TLS).

### 💳 Pagos y Frontend
* **Pasarela de Pagos:** Integración segura con servicios externos como **Webpay** y **PayPal** para transacciones en línea.
* **Interfaz Responsiva:** Diseño adaptable a móviles y escritorio utilizando HTML5, CSS3 y Bootstrap.

---

## 🚀 Instalación y Despliegue

Este proyecto utiliza **XAMPP** para el entorno local y requiere tener instalado Python para los microservicios.

1.  **Clonar el repositorio:**
    ```bash
    git clone [https://github.com/BitwareT/Bitware.git](https://github.com/BitwareT/Bitware.git)
    ```
2.  **Configurar Base de Datos:**
    * Importar el archivo `bitware_db.sql` en tu servidor MySQL local.
3.  **Microservicios IA:**
    * Navegar a la carpeta `/ai-services` e instalar dependencias:
    ```bash
    pip install -r requirements.txt
    python main.py
    ```

---

## 🏗️ Arquitectura del Sistema

El sistema sigue un patrón **MVC (Modelo-Vista-Controlador)** complementado con una arquitectura de microservicios para la IA:

* **Frontend:** HTML5, JS, Bootstrap.
* **Backend:** PHP 8 Nativo.
* **Base de Datos:** MySQL Relacional.
* **IA Services:** Python (API REST).
* **Infraestructura:** Despliegue en VPS Cloud.

---

## 👥 Autores

Equipo de desarrollo Full Stack:

* **David Cabezas** - *Coordinación, QA, Full Stack (Frontend/Backend/BD) & IA Integration*
* **Dilan Araos** - *Full Stack (Frontend/Backend) & Base de Datos*
* **Felipe Toro** - *Full Stack (Frontend/Backend), Arquitectura & Seguridad*

---
