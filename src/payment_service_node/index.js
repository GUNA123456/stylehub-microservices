/**
 * StyleHub - Node.js Payment Processing Microservice
 */

const express = require('express');
const { v4: uuidv4 } = require('uuid');

const app = express();
app.use(express.json());

const PORT = process.env.PORT || 8088;

app.get('/healthz', (req, res) => {
    res.json({ status: 'ok', service: 'node-payment-service' });
});

app.post('/api/payment/charge', (req, res) => {
    const { amount, credit_card } = req.body;

    if (!credit_card || !credit_card.credit_card_number) {
        return res.status(400).json({ error: 'Invalid credit card information' });
    }

    const transaction_id = `TX-NODE-${uuidv4().substring(0, 8).toUpperCase()}`;
    console.log(`💳 [NODE PAYMENT] Processed ${amount.units} ${amount.currency_code || 'USD'} | Tx: ${transaction_id}`);

    res.json({
        transaction_id,
        status: 'CHARGED',
        processor: 'StyleHub Node.js Payment Engine'
    });
});

app.listen(PORT, () => {
    console.log(`🚀 Node.js Payment Service running on port ${PORT}`);
});
