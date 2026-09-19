# 💼 FinancialApp - Plataforma Profesional de Gestión Financiera Personal

![Python](https://img.shields.io/badge/Python-3.12%2B-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%2B-336791?logo=postgresql)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0%2B-red)
![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?logo=chartdotjs)
![Bootstrap](https://img.shields.io/badge/Bootstrap-5.3-7952B3?logo=bootstrap)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)

**FinancialApp** es una aplicación web integral, profesional y moderna desarrollada en Python con **FastAPI**, **SQLAlchemy** y **PostgreSQL**, diseñada para administrar y visualizar en un solo lugar todas tus finanzas personales: cuentas bancarias, efectivo, tarjetas de crédito, tarjetas de débito, ingresos, gastos, transferencias entre cuentas, presupuestos mensuales y salud crediticia.

---

## 🌟 Características Principales por Módulo

### 1. 🔐 Autenticación y Seguridad
* Registro, inicio de sesión y gestión de perfil de usuario.
* Cifrado seguro de contraseñas con **Bcrypt**.
* Generación y validación de tokens de acceso **JWT (JSON Web Tokens)**.
* **Rate Limiting** en memoria contra ataques de fuerza bruta en endpoints de autenticación.
* **Cabeceras de Seguridad HTTP (OWASP)**: *X-Frame-Options*, *X-Content-Type-Options*, *Referrer-Policy*, *Content-Security-Policy* y *Permissions-Policy*.
* Aislamiento estricto de datos: cada usuario solo accede a sus propios registros.

### 2. 🏦 Cuentas Bancarias y Efectivo
* Soporte nativo para los principales bancos de Ecuador:
  * *Banco Pichincha, Banco Guayaquil, Banco del Pacífico, Produbanco, Banco Bolivariano, Banco Internacional, Banco del Austro, Banco Solidario, Banco General Rumiñahui (BGR), Banco de Loja y Efectivo*.
* Clasificación por tipos de cuenta: Corriente, Ahorros, Efectivo, Inversiones u Otros.
* Asignación visual de colores corporativos del banco y número de cuenta enmascarado (`****1234`).
* Ajuste directo de saldo con historial de motivos.

### 3. 💳 Tarjetas de Crédito y Débito
* Representación visual en formato de **tarjeta de plástico realista** (chip dorado, degradados y logotipos de franquicias: Visa, Mastercard, Diners Club, AMEX, Discover).
* Control de **límites de crédito, saldo utilizado / deuda y cupo disponible**.
* Indicador de salud crediticia con cálculo en vivo de la **tasa de utilización** (<30% Saludable, 30-60% Moderado, >60% Riesgo).
* Algoritmo inteligente de calendario para **fechas de corte y recordatorios de fechas de pago** sin intereses.

### 4. ↔️ Movimientos y Sincronización Automática de Saldos
* Registro de **Ingresos, Gastos, Transferencias y Pagos de Tarjetas**.
* **Motor Financiero Atómico**:
  * **Ingreso**: Aumenta automáticamente el saldo de la cuenta receptora.
  * **Gasto con Débito/Efectivo**: Reduce el saldo de la cuenta bancaria.
  * **Gasto con Tarjeta de Crédito**: Aumenta la deuda de la tarjeta y reduce su cupo disponible.
  * **Transferencia entre Cuentas**: Resta de la Cuenta A y suma a la Cuenta B (sin alterar ingresos/gastos globales).
  * **Pago de Tarjeta**: Resta de la cuenta pagadora y amortiza la deuda de la tarjeta de crédito.
* **Reversión Automática**: Al editar o eliminar cualquier movimiento, los saldos vuelven exactamente a su estado anterior.
* Catálogo de categorías predeterminadas y soporte para categorías personalizadas con iconos de Bootstrap y paleta de colores.

### 5. 📊 Dashboard Principal con Gráficos Chart.js
* Métricas financieras consolidadas: **Patrimonio Neto, Dinero Disponible, Deuda Total y Tasa de Ahorro**.
* 4 Gráficos interactivos en tiempo real con **Chart.js**:
  1. *Gastos por Categoría (Doughnut Chart)*.
  2. *Comparativa Mensual Ingresos vs Gastos (Bar Chart de 6 meses)*.
  3. *Distribución de Fondos por Banco (Pie Chart)*.
  4. *Deuda vs Límite de Tarjetas de Crédito (Bar Chart)*.
* Panel de vencimientos próximos y tabla de últimos movimientos.

### 6. 🥧 Presupuestos, Alertas y Reportes
* Fijación de límites de gasto mensual por categoría.
* Monitoreo en vivo con barras de progreso cromáticas (Verde, Amarillo, Rojo).
* **Centro de Alertas Financieras**:
  * Alertas de presupuestos excedidos o próximos al límite.
  * Alertas de vencimientos de tarjeta en menos de 3 días.
  * Alertas de alta utilización de crédito.
* **Exportación de Reportes**: Descarga de transacciones en archivo **CSV compatible con Microsoft Excel** (BOM UTF-8).

---

## 🏛️ Arquitectura del Proyecto

```
FinancialApp/
├── app/
│   ├── auth/                 # Seguridad JWT, hashing bcrypt y dependencias
│   │   ├── dependencies.py
│   │   └── security.py
│   ├── models/               # Modelos ORM de SQLAlchemy
│   │   ├── account.py        # Cuentas bancarias y efectivo
│   │   ├── budget.py         # Presupuestos mensuales
│   │   ├── card.py           # Tarjetas de crédito y débito
│   │   ├── category.py       # Categorías de ingresos/gastos
│   │   ├── transaction.py    # Movimientos financieros
│   │   └── user.py           # Usuarios
│   ├── routers/              # Controladores y endpoints de la API REST
│   │   ├── accounts.py
│   │   ├── auth.py
│   │   ├── budgets.py
│   │   ├── cards.py
│   │   ├── categories.py
│   │   ├── dashboard.py
│   │   ├── health.py
│   │   └── transactions.py
│   ├── schemas/              # Validación y serialización con Pydantic v2
│   │   ├── account.py
│   │   ├── budget.py
│   │   ├── card.py
│   │   ├── category.py
│   │   ├── dashboard.py
│   │   ├── health.py
│   │   ├── token.py
│   │   ├── transaction.py
│   │   └── user.py
│   ├── security/             # Middlewares de seguridad OWASP y Rate Limiting
│   │   ├── middleware.py
│   │   └── rate_limiter.py
│   ├── services/             # Lógica de negocio y motor de cálculos
│   │   ├── account_service.py
│   │   ├── budget_service.py
│   │   ├── card_service.py
│   │   ├── category_service.py
│   │   ├── dashboard_service.py
│   │   ├── transaction_service.py
│   │   └── user_service.py
│   ├── utils/                # Constantes y catálogos de bancos de Ecuador
│   │   └── constants.py
│   ├── config.py             # Configuración centralizada con Pydantic Settings
│   ├── database.py           # Conexión y sesión de base de datos PostgreSQL
│   └── main.py               # Punto de entrada de FastAPI y rutas web
├── frontend/
│   ├── static/               # CSS, JS y recursos estáticos
│   └── templates/            # Plantillas HTML con Jinja2 y Bootstrap 5
│       ├── base.html
│       ├── index.html
│       ├── login.html
│       ├── register.html
│       ├── accounts.html
│       ├── cards.html
│       ├── transactions.html
│       ├── dashboard.html
│       └── budgets.html
├── .dockerignore
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

---

## 🚀 Instalación y Puesta en Marcha

### Opción A: Ejecución Local en Windows / Linux / macOS

#### 1. Clonar el repositorio y crear entorno virtual
```powershell
# Crear y activar entorno virtual
python -m venv venv
.\venv\Scripts\Activate.ps1   # En Windows
# source venv/bin/activate    # En Linux / macOS
```

#### 2. Instalar dependencias
```powershell
pip install -r requirements.txt
```

#### 3. Configurar variables de entorno
Crea tu archivo `.env` a partir de la plantilla:
```powershell
cp .env.example .env
```

Configura tu cadena de conexión a PostgreSQL en `.env`:
```env
DATABASE_URL=postgresql+psycopg2://postgres:postgres@localhost:5432/financial_db
SECRET_KEY=clave_secreta_super_segura_de_produccion_123456789
```

#### 4. Iniciar la base de datos PostgreSQL (con Docker)
```powershell
docker run --name financial_postgres -e POSTGRES_USER=postgres -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=financial_db -p 5432:5432 -d postgres:16
```

#### 5. Ejecutar la aplicación
```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

---

### Opción B: Despliegue en 1 Clic con Docker Compose

Para desplegar tanto la aplicación web como la base de datos PostgreSQL en contenedores aislados de producción:

```bash
docker compose up -d --build
```

Para detener los servicios:
```bash
docker compose down
```

---

## 🌐 Enlaces de Acceso y Rutas Web

Una vez iniciada la aplicación, accede desde tu navegador:

| Módulo | URL Local | Descripción |
| :--- | :--- | :--- |
| **Inicio** | `http://127.0.0.1:8000/` | Portada y accesos rápidos |
| **Dashboard** | `http://127.0.0.1:8000/dashboard` | Gráficos Chart.js, patrimonio y KPIs |
| **Cuentas** | `http://127.0.0.1:8000/accounts` | Cuentas bancarias de Ecuador y efectivo |
| **Tarjetas** | `http://127.0.0.1:8000/cards` | Tarjetas plásticas, límites y fechas de corte/pago |
| **Movimientos** | `http://127.0.0.1:8000/transactions` | Ingresos, gastos, transferencias y pagos |
| **Presupuestos** | `http://127.0.0.1:8000/budgets` | Topes mensuales por categoría y reportes CSV |
| **Documentación Swagger** | `http://127.0.0.1:8000/docs` | Interfaz interactiva para probar endpoints REST |
| **Documentación ReDoc** | `http://127.0.0.1:8000/redoc` | Especificación técnica OpenAPI |
| **Health Check** | `http://127.0.0.1:8000/api/v1/health` | Diagnóstico de salud y conexión con la base de datos |

---

## 🛡️ Seguridad y Buenas Prácticas

1. **Sin Almacenamiento de Credenciales Sensibles**:
   * Nunca se guardan números de tarjeta completos (solo últimos 4 dígitos) ni códigos CVV.
2. **Cifrado Robusto**:
   * Contraseñas con hashing unidireccional Bcrypt con salt automático.
3. **Protección de Tráfico**:
   * Rate limiting para mitigar ataques de fuerza bruta.
   * Cabeceras HTTP seguras configuradas según estándares OWASP.
4. **Transaccionalidad en Base de Datos**:
   * Toda operación de ingresos, gastos, transferencias y pagos se ejecuta de manera atómica (`db.commit()`), garantizando que los saldos nunca queden en estados inconsistentes.

---

**FinancialApp** &copy; 2026 &bull; Desarrollado con FastAPI, PostgreSQL y Chart.js.
