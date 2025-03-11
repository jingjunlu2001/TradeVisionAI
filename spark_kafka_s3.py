from pyspark.sql import SparkSession
from pyspark.sql.functions import from_json, col, expr, explode
from pyspark.sql.types import StructType, StructField, FloatType, TimestampType, LongType, StringType, MapType
import os

# Initialize Spark Session
spark = SparkSession.builder \
    .appName("KafkaToS3") \
    .master("local[*]") \
    .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.1,org.apache.spark:spark-sql-kafka-0-10_2.12:3.2.1") \
    .config("spark.hadoop.fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    .config("spark.hadoop.fs.s3a.access.key", os.getenv("TradeVisionAI_S3_Access_Key")) \
    .config("spark.hadoop.fs.s3a.secret.key", os.getenv("TradeVisionAI_S3_Secret_Key")) \
    .getOrCreate()

# Kafka Configuration
KAFKA_BROKER = "localhost:9092"
TOPIC_NAME = "alphavantage_intraday_api_data"

# Define schema for OHLCV data
ohlcv_schema = StructType([
    StructField("1. open", StringType(), True),
    StructField("2. high", StringType(), True),
    StructField("3. low", StringType(), True),
    StructField("4. close", StringType(), True),
    StructField("5. volume", StringType(), True)
])

# Define the schema for the full JSON message
message_schema = MapType(StringType(), ohlcv_schema)

# Read from Kafka
df_raw = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_BROKER) \
    .option("subscribe", TOPIC_NAME) \
    .option("startingOffsets", "latest") \
    .load()

# Parse Kafka message value as JSON
df_json = df_raw.selectExpr("CAST(value AS STRING) as json_data")

# Convert JSON string to a structured DataFrame
df_structured = df_json.select(from_json(col("json_data"), message_schema).alias("data"))

# Explode the Map to get individual timestamp and OHLCV data
df_exploded = df_structured.selectExpr("explode(data) as (timestamp, ohlcv)")

# Extract and rename columns (no need to explode)
df_final = df_exploded.select(
    col("timestamp"),
    col("ohlcv.`1. open`").alias("open"),
    col("ohlcv.`2. high`").alias("high"),
    col("ohlcv.`3. low`").alias("low"),
    col("ohlcv.`4. close`").alias("close"),
    col("ohlcv.`5. volume`").alias("volume")
)

# # Display the data in the stream to the console for debugging
# query = df_final \
#     .writeStream \
#     .outputMode("append") \
#     .format("console") \
#     .start()

# Define S3 Path (Adjust bucket name)
S3_BUCKET = os.getenv("TradeVisionAI_S3_Bucket_Name")
S3_CHECKPOINT = os.getenv("TradeVisionAI_S3_Spark_Ckpt")


# Write to AWS S3 in Parquet format
query = df_final.writeStream \
    .outputMode("append") \
    .format("parquet") \
    .option("checkpointLocation", S3_CHECKPOINT) \
    .option("path", S3_BUCKET) \
    .start()

query.awaitTermination()