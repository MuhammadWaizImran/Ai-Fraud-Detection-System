# Databricks Notebook: 01_bronze_ingestion.py
# Cell 1 - Load secrets from Key Vault-backed secret scope
# NOTE: Run with trigger(availableNow=True) on Serverless compute.
# For continuous streaming: re-run via Databricks Job schedule.

# ─── Cell 1: Config from Key Vault secret scope ───────────────────────────────
eventhub_conn_string = dbutils.secrets.get(scope="fraud-kv-scope", key="eventhub-conn-string")
eh_namespace = dbutils.secrets.get(scope="fraud-kv-scope", key="eventhub-namespace")
eh_name = dbutils.secrets.get(scope="fraud-kv-scope", key="eventhub-name")
storage_account = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-name")
storage_key = dbutils.secrets.get(scope="fraud-kv-scope", key="storage-account-key")

# Configure Spark to access ADLS Gen2 via storage key
spark.conf.set(
    f"fs.azure.account.key.{storage_account}.dfs.core.windows.net",
    storage_key
)

CATALOG   = "fraud_detection_catalog"
BRONZE_DB = "bronze"
TABLE     = "raw_trades"
CHECKPOINT = f"abfss://checkpoints@{storage_account}.dfs.core.windows.net/bronze_raw_trades"

print(f"Event Hub NS  : {eh_namespace}")
print(f"Event Hub Name: {eh_name}")
print(f"Storage       : {storage_account}")
print(f"Checkpoint    : {CHECKPOINT}")

# ─── Cell 2: Read streaming from Event Hubs via Kafka protocol ────────────────
bootstrap_server = f"{eh_namespace}.servicebus.windows.net:9093"

jaas_config = (
    'kafkashaded.org.apache.kafka.common.security.plain.PlainLoginModule required '
    f'username="$ConnectionString" password="{eventhub_conn_string}";'
)

kafka_options = {
    "kafka.bootstrap.servers":  bootstrap_server,
    "subscribe":                eh_name,
    "kafka.sasl.mechanism":     "PLAIN",
    "kafka.security.protocol":  "SASL_SSL",
    "kafka.sasl.jaas.config":   jaas_config,
    "startingOffsets":          "earliest",
    "failOnDataLoss":           "false",
    "kafka.request.timeout.ms": "60000",
    "kafka.session.timeout.ms": "30000",
}

raw_stream = (
    spark.readStream
    .format("kafka")
    .options(**kafka_options)
    .load()
)

# ─── Cell 3: Parse and project bronze schema ──────────────────────────────────
from pyspark.sql.functions import col, current_timestamp

bronze_df = raw_stream.selectExpr(
    "CAST(value AS STRING) AS json_str",
    "timestamp              AS kafka_enqueued_time",
    "partition              AS kafka_partition",
    "offset                 AS kafka_offset",
    "topic                  AS kafka_topic"
).withColumn("ingested_at", current_timestamp())

# ─── Cell 4: Write to Bronze Delta table ─────────────────────────────────────
(
    bronze_df.writeStream
    .format("delta")
    .outputMode("append")
    .option("checkpointLocation", CHECKPOINT)
    .trigger(availableNow=True)           # Serverless-compatible - processes available data then stops
    .toTable(f"{CATALOG}.{BRONZE_DB}.{TABLE}")
)

print(f"Bronze ingestion complete -> {CATALOG}.{BRONZE_DB}.{TABLE}")
spark.sql(f"SELECT COUNT(*) AS row_count FROM {CATALOG}.{BRONZE_DB}.{TABLE}").show()
