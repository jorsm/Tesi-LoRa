const express = require("express");
const bodyParser = require("body-parser");
const PORT = process.env.PORT || 3000;

let app = express();
app.use(bodyParser.urlencoded({ extended: false }));
app.use(bodyParser.json());
app.set("views", __dirname + "/views");
app.set("view engine", "ejs");

app.use(express.urlencoded({ extended: false }));
app.use(express.static(__dirname + "/public"));

/**
 * Database stuff
 */
const dbUser = "";
const dbName = "";

const dbUrl = `mongodb+srv://user:${dbUser}@$cluster0.cvkqx.mongodb.net/${dbName}?retryWrites=true&w=majority`;
const mongoose = require("mongoose");
mongoose.connect(dbUrl, { useNewUrlParser: true, useUnifiedTopology: true });
const db = mongoose.connection;

let Misura;
db.on("error", console.error.bind(console, "connection error:"));
db.once("open", function () {
  const misuraSchema = new mongoose.Schema({
    pInterf: Number, //Prob interf
    txRx: Number, //distance between TX and RX
    rxInt: Number,
    initParams: Object, //Initial CR, DR
    data: Array, //Collected data
    timestamp: { type: Date, default: Date.now() },
  });
  Misura = mongoose.model("Misura", misuraSchema);
});

var browserSync = require("browser-sync");
const { get } = require("browser-sync");
var bs = browserSync.create().init({ logSnippet: false });
app.use(require("connect-browser-sync")(bs));

/**
 * Initialize server and devices status params
 */
let lora_rx_status = { dr: -1 };
let lora_tx_status = { dr: -1, cr: 1 };
let times = [];
let pending_ids = [];
let reset = false;

let messages = [];
let configs = [];

let int_count = 0;

app.get("/", (req, res) => {
  res.render("index", { messages, configs });
});

/**
 *  Meccanismo di Reset della misura
 *    ogni 10 pacchetti inviati TX controlla il valore di 'reset'
 *    true -> si resetta
 *    RX vede il reset di TX e si resetta a sua volta
 */
app.get("/set_tx_reset", (req, res) => {
  reset = true;
  res.redirect("/");
});

app.get("/reset", (req, res) => {
  res.json({ reset: reset });
  reset = false;
});
/**
 * Aggiunge una configurazione per una misura
 */
app.post("/add_config", (req, res) => {
  let { tx_rx, rx_int, pr_int, dr, cr } = req.body;
  let config = {
    pInterf: Number(pr_int), //prob interferenza
    txRx: Number(tx_rx), // distanza TX - RX
    rxInt: Number(rx_int), // distanza  RX - INT
    initParams: { cr: cr, dr: dr }, // DataRate e CodeRate da cui iniziare
  };
  configs.push(config);
  res.redirect("/");
});
/**
 * Rimuove una configurazione dalla lista  'configs'
 */
app.get("/del_config", (req, res) => {
  let del_index = parseInt(req.query.id);
  configs = configs.filter((conf, index) => index !== del_index);
  res.redirect("/");
});
/**
 * Riceve e filtra messaggi da visualizzare e relativi mittenti
 */
app.post("/messages", (req, res) => {
  let { sender, message } = req.body;
  console.log("New Message! " + JSON.stringify(req.body));
  //filtro messaggi ripetuti inutili
  if (message.includes("Sent")) {
    if (messages[messages.length - 1].message.includes("Sent")) messages.pop();
  }
  if (message.includes("[RX.LoRa] Unknown target CR")) {
    if (
      messages[messages.length - 1].message.includes(
        "[RX.LoRa] Unknown target CR"
      )
    ) {
      messages.pop();
      int_count = int_count + 1;
      message = int_count.toString() + "x " + message;
    }
  }
  //update Coding Rate
  if (message.includes("    > Coding Rate: ")) {
    lora_tx_status.cr = parseInt(
      message.substring(message.length - 2, message.length)
    );
  }
  let msg = {
    sender: sender,
    message: message,
    timestamp: new Date().toISOString(),
  };
  messages.push(msg);
  console.log(
    `%c[${new Date().toISOString()}] : [MESSAGE] From: ${req.body.sender}: ${
      req.body.message
    }`,
    "color:blue;"
  );

  res.status(200).send("ok");
});
/**
 * restituisce il CR attuale di TX, serve a RX e INT  per regolarsi di conseguenza
 */
app.get("/cr", (req, res) => {
  res.send({ cr: lora_tx_status.cr });
});
/**
 *  Salva i dati raccolti nel database
 *  Resetta i parametri sul server
 *  Attende una nuova configurazione e che TX sia pronto
 */
app.get("/reset_stats", (req, res) => {
  config = configs.shift(); //update to new config
  const misura = new Misura({ ...config, data: times }); //save data
  misura.save(function (err, result) {
    if (err) {
      throw err;
    }
    console.log("Misura salvata nel database");
  });
  //reset dashboard messages
  messages = [
    {
      sender: "Server",
      message: "Waiting for configs or for TX to finish setup!",
      timestamp: new Date().toISOString(),
    },
  ];
  //reset server params
  times = [];
  pending_ids = [];
  lora_rx_status = { dr: -1, cr: 1 };
  interf_counter = 0;
  reset = false;

  console.log(`[${new Date().toISOString()}] : Server stats reset`);
  if (configs.length == 0) {
    res.json({ dr: -1 }); //  wait for a valid config
  } else {
    res.json(configs[0].initParams);
  }
});

app.get("/stats", (req, res) => {
  res.json(times);
  console.log(
    `[${new Date().toISOString()}] : [GET] stats \n ${JSON.stringify(times)}`
  );
});
/*
 *  TX aspetta che RX sia pronto prima di iniziare ad inviare pacchetti
 */
app.get("/rx_status", (req, res) => {
  res.json(lora_rx_status);
  console.log(
    `[${new Date().toISOString()}] : [GET] rx_status: ${JSON.stringify(
      lora_rx_status
    )}`
  );
});

app.post("/rx_status", (req, res) => {
  //update setver param
  if (req.body.dr !== undefined) {
    lora_rx_status.dr = parseInt(req.body.dr);
    console.log(
      `[${new Date().toISOString()}] : [POST] RX.dr -> ` + lora_rx_status.dr
    );
  }

  // First try to parse pending IDs
  //pending = packetID not received yet
  var still_pending = [];
  pending_ids.forEach((x) => {
    if (times[x] !== undefined) times[x].confirmed = true;
    else still_pending.push(x);
  });
  pending_ids = still_pending;
  //update server with IDs of reveived packets
  if (req.body.recv_ids !== undefined)
    req.body.recv_ids.forEach((x) => {
      if (times[x] !== undefined) times[x].confirmed = true;
      else pending_ids.push(x);
    });

  res.send("ok");
});
//permette a RX e INT di capire quando TX ha inizito e trasmettere e con quali CR e DR
// manda anche la pInterf per il setup del draghino shield (INT)
app.get("/tx_status", (req, res) => {
  let { dr, cr } = lora_tx_status;
  let pr_int = configs.length > 0 ? configs[0].pInterf : 0;
  res.json({ dr, cr, pr_int });
  console.log(
    `[${new Date().toISOString()}] : [GET] tx_status: ` +
      JSON.stringify(lora_tx_status)
  );
});

app.post("/tx_status", (req, res) => {
  if (req.body.dr !== undefined) {
    lora_tx_status.dr = parseInt(req.body.dr);
    console.log(
      `[${new Date().toISOString()}] : [POST] TX.dr -> ` + lora_tx_status.dr
    );
  }
  //sent packets
  if (req.body.time_stats !== undefined) {
    req.body.time_stats.forEach((x) => {
      times[x.id] = {
        id: x.id,
        dr: x.dr,
        cr: x.cr,
        size: x.size,
        time_ms: x.time_ms,
        confirmed: false,
      };
    });
  }

  res.send("ok");
});

server = app.listen(PORT, () => console.log(`Listening on port ${PORT}...`));
