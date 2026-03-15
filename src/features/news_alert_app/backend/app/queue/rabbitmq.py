import json
import pika
from app.core.config import settings

def publish(queue_name: str, payload: dict):
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)
    channel.basic_publish(
        exchange="",
        routing_key=queue_name,
        body=json.dumps(payload),
        properties=pika.BasicProperties(delivery_mode=2),
    )
    connection.close()

def consumer(
    queue_name: str,
    handler,
    *,
    stop_when_idle: bool = False,
    inactivity_timeout: float = 3.0,
    max_messages: int | None = None,
):
    params = pika.URLParameters(settings.rabbitmq_url)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=queue_name, durable=True)

    if stop_when_idle:
        processed = 0
        print(f" Draining {queue_name} until idle...")
        try:
            for method, properties, body in channel.consume(
                queue=queue_name,
                inactivity_timeout=inactivity_timeout,
                auto_ack=False,
            ):
                if method is None:
                    break

                payload = json.loads(body)
                handler(payload)
                channel.basic_ack(delivery_tag=method.delivery_tag)

                processed += 1
                if max_messages is not None and processed >= max_messages:
                    break

            channel.cancel()
            print(f" Drained {processed} message(s) from {queue_name}.")
        finally:
            connection.close()
        return

    def callback(ch, method, properties, body):
        payload = json.loads(body)
        handler(payload)
        ch.basic_ack(delivery_tag=method.delivery_tag)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue_name, on_message_callback=callback)
    print(f" Consuming from {queue_name}...")
    channel.start_consuming()
