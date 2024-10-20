ia@ia-desktop:~/Documents/meus apps/screenshare2-test/backend$ npm start

> screenshare-backend@1.0.0 start
> node server.js

Server running on port 5000
Killed
ia@ia-desktop:~/Documents/meus apps/screenshare2-test/backend$ npm start

> screenshare-backend@1.0.0 start
> node server.js

node:events:497
      throw er; // Unhandled 'error' event
      ^

Error: listen EADDRINUSE: address already in use :::5001
    at Server.setupListenHandle [as _listen2] (node:net:1904:16)
    at listenInCluster (node:net:1961:12)
    at Server.listen (node:net:2063:7)
    at Object.<anonymous> (/home/ia/Documents/meus apps/screenshare2-test/backend/server.js:84:8)
    at Module._compile (node:internal/modules/cjs/loader:1469:14)
    at Module._extensions..js (node:internal/modules/cjs/loader:1548:10)
    at Module.load (node:internal/modules/cjs/loader:1288:32)
    at Module._load (node:internal/modules/cjs/loader:1104:12)
    at Function.executeUserEntryPoint [as runMain] (node:internal/modules/run_main:174:12)
    at node:internal/main/run_main_module:28:49
Emitted 'error' event on Server instance at:
    at emitErrorNT (node:net:1940:8)
    at process.processTicksAndRejections (node:internal/process/task_queues:82:21) {
  code: 'EADDRINUSE',
  errno: -98,
  syscall: 'listen',
  address: '::',
  port: 5001
}

Node.js v20.17.0
ia@ia-desktop:~/Documents/meus apps/screenshare2-test/backend$ 
