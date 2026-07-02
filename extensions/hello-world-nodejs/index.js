const http = require('http');

const PORT = process.env.PORT || 3000;

const server = http.createServer((req, res) => {
  res.setHeader('Content-Type', 'application/json');
  res.writeHead(200);
  res.end(JSON.stringify({ message: 'Hello from Node.js on Posit Connect!' }));
});

server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});
