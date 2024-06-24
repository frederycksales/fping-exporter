from prometheus_client import start_http_server, Gauge
import subprocess
import time

# Configurar os alvos
TARGETS = ["8.8.8.8", "8.8.4.4", "1.1.1.1"]

# Configurar as métricas Prometheus
FPING_LATENCY = Gauge('fping_latency', 'Latency in ms', ['target'])
FPING_LOSS = Gauge('fping_loss', 'Packet loss in percent', ['target'])


def ping_target(target):
    try:
        result = subprocess.run(
            ['fping', '-c1', '-t500', target],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        # Inicializar valores padrão
        latency = -1
        loss = 100

        # Extrair a latência e o loss do resultado do fping
        for line in result.stdout.split('\n'):
            if 'bytes from' in line:
                latency = float(line.split('=')[-1].replace('ms', '').strip())
            if 'xmt/rcv/%loss' in line:
                loss = float(line.split('/')[-1].replace('%', '').strip())

        return latency, loss
    except Exception as e:
        print(f"Error pinging target {target}: {e}")
        return -1, 100


if __name__ == "__main__":
    # Iniciar o servidor HTTP do Prometheus
    start_http_server(8000)

    while True:
        for target in TARGETS:
            latency, loss = ping_target(target)
            FPING_LATENCY.labels(target=target).set(latency)
            FPING_LOSS.labels(target=target).set(loss)
        # Esperar 60 segundos antes de coletar novamente
        time.sleep(60)
