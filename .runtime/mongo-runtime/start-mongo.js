const fs = require('fs');
const path = require('path');
const { MongoMemoryServer } = require('mongodb-memory-server');

async function main() {
  const dataDir = path.join(__dirname, 'data');
  fs.mkdirSync(dataDir, { recursive: true });

  const mongod = await MongoMemoryServer.create({
    instance: {
      dbName: 'test_database',
      dbPath: dataDir,
      port: 27017,
      storageEngine: 'wiredTiger',
    },
  });

  console.log(`MongoDB started at ${mongod.getUri()}`);

  const shutdown = async () => {
    await mongod.stop();
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  await new Promise(() => {});
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
