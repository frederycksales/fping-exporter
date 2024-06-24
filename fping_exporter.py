#!/usr/bin/python3
from prometheus_client import start_http_server, Gauge
import subprocess
import time
import logging

# Configurar o logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s', handlers=[
    logging.FileHandler("/tmp/fping_exporter.log"),
    logging.StreamHandler()
])

# Configurar os alvos
TARGETS = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]

# Configurar as métricas Prometheus
FPING_LATENCY = Gauge('fping_latency', 'Latency in ms', ['target', 'type'])
FPING_LOSS = Gauge('fping_loss', 'Packet loss in percent', ['target'])
FPING_SENT = Gauge('fping_sent', 'Packets sent', ['target'])
FPING_RECEIVED = Gauge('fping_received', 'Packets received', ['target'])
LOOP_DURATION = Gauge('loop_duration_seconds', 'Time taken for one loop iteration')

def ping_targets(targets):
    try:
        result = subprocess.run(
            ['fping', '-c10', '-p1500', '-q', '-t500'] + targets,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Log do resultado do fping
        logging.info(f"fping result: {result.stderr.strip()}")

        metrics = {}

        # Inicializar valores padrão
        for target in targets:
            metrics[target] = {
                'min_latency': -1,
                'avg_latency': -1,
                'max_latency': -1,
                'loss': 100,
                'sent': 0,
                'received': 0
            }

        # Extrair a latência e a perda do resultado do fping
        for line in result.stderr.split('\n'):
            logging.info(f"Processing line: {line}")
            if 'xmt/rcv/%loss' in line:
                parts = line.split()
                target = parts[0]
                logging.info(f"Parts for sent, received, and loss: {parts}")

                sent_received_loss = parts[4].replace(',', '').replace('%', '').split('/')
                logging.info(f"Extracted sent/received/loss: {sent_received_loss}")
                metrics[target]['sent'] = float(sent_received_loss[0])
                metrics[target]['received'] = float(sent_received_loss[1])
                metrics[target]['loss'] = float(sent_received_loss[2])

            if 'min/avg/max' in line:
                parts = line.split()
                target = parts[0]
                logging.info(f"Parts for latency: {parts}")

                latency_values = parts[7].split('/')
                logging.info(f"Extracted latency values: {latency_values}")
                metrics[target]['min_latency'] = float(latency_values[0])
                metrics[target]['avg_latency'] = float(latency_values[1])
                metrics[target]['max_latency'] = float(latency_values[2])

        return metrics
    except Exception as e:
        logging.error(f"Error pinging targets: {e}")
        return {target: {'min_latency': -1, 'avg_latency': -1, 'max_latency': -1, 'loss': 100, 'sent': 0, 'received': 0} for target in targets}

if __name__ == "__main__":
    # Iniciar o servidor HTTP do Prometheus
    logging.info("Starting Prometheus HTTP server on port 8000")
    start_http_server(8000)

    while True:
        start_time = time.time()
        metrics = ping_targets(TARGETS)
        for target, metric in metrics.items():
            logging.info(f"Metrics for target {target} - Min latency: {metric['min_latency']} ms, Avg latency: {metric['avg_latency']} ms, Max latency: {metric['max_latency']} ms, Loss: {metric['loss']}%, Sent: {metric['sent']}, Received: {metric['received']}")
            FPING_LATENCY.labels(target=target, type='min').set(metric['min_latency'])
            FPING_LATENCY.labels(target=target, type='avg').set(metric['avg_latency'])
            FPING_LATENCY.labels(target=target, type='max').set(metric['max_latency'])
            FPING_LOSS.labels(target=target).set(metric['loss'])
            FPING_SENT.labels(target=target).set(metric['sent'])
            FPING_RECEIVED.labels(target=target).set(metric['received'])
        end_time = time.time()
        loop_duration = end_time - start_time
        logging.info(f"Loop duration: {loop_duration} seconds")
        LOOP_DURATION.set(loop_duration)
        # Esperar 1 segundo antes de coletar novamente
        logging.info("Sleeping for 1 second")
        time.sleep(1)
