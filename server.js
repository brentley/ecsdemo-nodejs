// use the express framework
var express = require('express');
var app = express();

var fs = require('fs');
var code_hash = fs.readFileSync('code_hash.txt','utf8');
console.log (code_hash);

// internal-ip: detect the correct IP based on default gw
var internalip = require('internal-ip');
var ipaddress = internalip.v4.sync();

// use ipaddress to find interface netmask
var ifaces = require('os').networkInterfaces();
for (var dev in ifaces) {
  // ... and find the one that matches the criteria
  var iface = ifaces[dev].filter(function(details) {
    return details.address === `${ipaddress}` && details.family === 'IPv4';
  });
  if(iface.length > 0) ifacenetmask = iface[0].netmask;
}

// ip: separate out the network using the subnet mask
var ipnet = require('ip');
var network = ipnet.mask(`${ipaddress}`, `${ifacenetmask}`)

// morgan: generate apache style logs to the console
var morgan = require('morgan')
app.use(morgan('combined'));

// express-healthcheck: respond on /health route for LB checks
app.use('/health', require('express-healthcheck')());

// label the AZ based on which subnet we are on
switch (network) {
  case '10.0.100.0':
    var az = '1a';
    break;
  case '10.0.101.0':
    var az = '1b';
    break;
  case '10.0.102.0':
    var az = '1c';
    break;
  default:
    var az = 'unknown'
    break;
}

// main route
app.get('/', function (req, res) {
  res.set({
  'Content-Type': 'text/plain'
})
  res.send(`Node.js backend: Hello! from ${ipaddress} in AZ-${az} commit ${code_hash}`);
  // res.send(`Hello World! from ${ipaddress} in AZ-${az} which has been up for ` + process.uptime() + 'ms');
});

// health route - variable subst is more pythonic just as an example
var server = app.listen(3000, function() {
  var port = server.address().port;
  console.log('Example app listening on port %s!', port);
  console.log("trigger-test");
});

// export the server to make tests work
module.exports = server;
