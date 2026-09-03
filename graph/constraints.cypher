CREATE CONSTRAINT customer_id IF NOT EXISTS FOR (c:Customer) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT merchant_id IF NOT EXISTS FOR (m:Merchant) REQUIRE m.id IS UNIQUE;
CREATE CONSTRAINT device_id IF NOT EXISTS FOR (d:Device) REQUIRE d.id IS UNIQUE;
CREATE CONSTRAINT instrument_id IF NOT EXISTS FOR (i:PaymentInstrument) REQUIRE i.id IS UNIQUE;
CREATE CONSTRAINT ip_id IF NOT EXISTS FOR (ip:IPAddress) REQUIRE ip.id IS UNIQUE;
CREATE CONSTRAINT transaction_id IF NOT EXISTS FOR (t:Transaction) REQUIRE t.id IS UNIQUE;
CREATE INDEX customer_status IF NOT EXISTS FOR (c:Customer) ON (c.status);
CREATE INDEX transaction_occurred IF NOT EXISTS FOR (t:Transaction) ON (t.occurred_at);
