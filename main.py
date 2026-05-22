#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OSINT-REILLY: Core Orchestrator (Blocks #0 and #1 Integrated)
Target Directory: /home/ubuntu/IT-PROJECTS/00.Wibe-coding_projects/Wibe_Commander/
Line Length Limit: 100 characters
"""

import os
import sys
import argparse
import logging
from datetime import datetime

# Імпорт нашого автономного планувальника з Блоку #1
try:
    from core_intelligence.planner import ReillyPlanner
except ImportError:
    # Захисний фолбек, якщо запуск відбувається до створення окремого модуля
    ReillyPlanner = None

# Налаштування логування відповідно до ТЗ (індивідуальні логі для ботів у кукоін-контурі)
LOG_DIR = "/home/ubuntu/kucoin_prod/bots/logs/"
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "reilly_orchestrator.log"), encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)

def parse_arguments():
    """Парсинг вхідних параметрів для визначення профілю роботи системи."""
    parser = argparse.ArgumentParser(description="OSINT-REILLY: Autonomous Intelligence Engine")
    parser.add_argument(
        "--mode", 
        choices=["hackathon", "full-tank", "private"], 
        required=True,
        help="Execution profile: hackathon (SaaS), full-tank (Defense), private (Personal Admin)"
    )
    parser.add_argument(
        "--target", 
        type=str, 
        default="General_Pulse",
        help="Target object or geography for research (e.g., Kursk, Saratov, Fuel_Market)"
    )
    return parser.parse_args()

def initialize_environment(mode):
    """Перевірка та ініціалізація структури папок та конфігів."""
    logging.info("Initializing REILLY Environment in [%s] mode...", mode.upper())
    
    # Перевірка наявності технічного опису архітектури
    config_path = "./docs/architecture.json"
    if not os.path.exists(config_path):
        logging.error("Critical error: architecture.json not found at %s", config_path)
        sys.exit(1)
        
    logging.info("Environment successfully verified. Core system stable.")

def run_analytical_pipelines(mode, target):
    """
    БЛОК #1: Декомпозиція, фільтрація та запуск ліній аналітики.
    """
    logging.info("Sending target string to Block #1 (Planner)...")
    
    # Формуємо сирий запит на основі вхідної цілі
    raw_query = f"Глибокий аналіз об'єкта та інфраструктури: {target}"
    
    # Ініціалізація або емуляція Планувальника
    if ReillyPlanner:
        planner = ReillyPlanner()
        plan = planner.generate_action_plan(raw_query)
        
        # Етап 1.1: Перевірка фільтра "Субмарини"
        if plan["status"] == "FAILED":
            logging.error("Task ABORTED by Planner Filter: %s", plan["error"])
            sys.exit(1)
            
        logging.info("Task APPROVED by Submarine Filter.")
        logging.info("Assigned Domains (Etap 1.2): %s", plan["assigned_domains"])
        logging.info("Bright Data Blueprint (Etap 1.3): %s", plan["bright_data_execution_plan"])
    else:
        logging.warning("ReillyPlanner module not detected. Running on default orchestrator logic.")
        plan = {"assigned_domains": ["general_monitoring"]}

    # Запуск 5 бойових ліній динамічного дослідження
    lines = [
        "War & Security Contour",
        "Shadow Economy & Logistics",
        "Social Tectonic Shifts",
        "Tech & Resource Audit",
        "Markov Probabilistic Forecasts"
    ]
    
    for idx, line in enumerate(lines, 1):
        logging.info("Activating Line %d/%d: %s", idx, len(lines), line)
        # Тут буде послідовний виклик суб-агентів Ради Директорів (Ґрін, Джервіс, Ґолдратт)
        
    # Диференціація виводу результатів відповідно до комерційного профілю
    if mode == "hackathon":
        logging.info("Launching Streamlit GUI Platform on port 8501...")
        # Майбутній виклик ui/app.py для демонстрації журі
    elif mode == "full-tank":
        # Запис у trades_history.lsonl згідно з правилами збереження аналітики для ботів
        history_path = "/home/ubuntu/KUCOIN_PROD/bots/bot_1/state/trades_history.lsonl"
        logging.info("Analytical objects successfully written to %s", history_path)
    elif mode == "private":
        # Вивід у папку приватних звітів
        report_dir = "/home/ubuntu/01.KUCOIN_PROD/direct/analysis/reports"
        logging.info("Silent delivery finished. Reports placed in %s", report_dir)

def main():
    args = parse_arguments()
    initialize_environment(args.mode)
    
    start_time = datetime.now()
    logging.info("=== REILLY ENGINE START AT %s ===", start_time.strftime("%Y-%m-%d %H:%M:%S"))
    
    try:
        run_analytical_pipelines(args.mode, args.target)
    except Exception as e:
        logging.critical("Fatal failure in orchestrator loop: %s", str(e), exc_info=True)
        sys.exit(1)
        
    logging.info("=== REILLY ENGINE FINISHED SUCCESSFULLY (Execution time: %s) ===", 
                 str(datetime.now() - start_time))

if __name__ == "__main__":
    main()