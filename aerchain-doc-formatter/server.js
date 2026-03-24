const express = require('express');
const Anthropic = require('@anthropic-ai/sdk');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { DESIGN_SYSTEM_PROMPT } = require('./design-system-prompt');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));
app.use(express.static(path.join(__dirname, 'public')));

// File upload config (for HTML/text file uploads)
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB
  fileFilter: (req, file, cb) => {
    const allowed = ['.html', '.htm', '.txt', '.md', '.csv', '.json'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowed.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error(`File type ${ext} not supported. Use: ${allowed.join(', ')}`));
    }
  }
});

// Health check
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', hasApiKey: !!process.env.ANTHROPIC_API_KEY });
});

// Main formatting endpoint
app.post('/api/format', upload.single('file'), async (req, res) => {
  try {
    const apiKey = req.headers['x-api-key'] || process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
      return res.status(400).json({
        error: 'No API key provided. Set ANTHROPIC_API_KEY env var or pass via x-api-key header.'
      });
    }

    // Get input content from either pasted text or uploaded file
    let inputContent = req.body.content || '';
    if (req.file) {
      inputContent = req.file.buffer.toString('utf-8');
    }

    if (!inputContent.trim()) {
      return res.status(400).json({ error: 'No content provided.' });
    }

    // Optional: user instructions for how to format
    const instructions = req.body.instructions || '';
    const selectedTheme = req.body.theme || 'purple-glass';

    // Build the user message
    let userMessage = `Reformat the following content into an Aerchain Dark Theme HTML document.\n`;
    if (instructions) {
      userMessage += `\nAdditional instructions: ${instructions}\n`;
    }
    userMessage += `\nSet the default active theme to "${selectedTheme}" (add data-theme="${selectedTheme}" to the body tag if it's not purple-glass, and mark the corresponding .td dot as active).\n`;
    userMessage += `\n---BEGIN CONTENT---\n${inputContent}\n---END CONTENT---`;

    const client = new Anthropic.default({ apiKey });

    // Use streaming for long responses
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const stream = await client.messages.stream({
      model: 'claude-sonnet-4-20250514',
      max_tokens: 16000,
      system: DESIGN_SYSTEM_PROMPT,
      messages: [{ role: 'user', content: userMessage }]
    });

    for await (const event of stream) {
      if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
        res.write(`data: ${JSON.stringify({ text: event.delta.text })}\n\n`);
      }
    }

    res.write(`data: ${JSON.stringify({ done: true })}\n\n`);
    res.end();

  } catch (err) {
    console.error('Format error:', err);
    // If headers already sent (streaming started), end the stream with error
    if (res.headersSent) {
      res.write(`data: ${JSON.stringify({ error: err.message })}\n\n`);
      res.end();
    } else {
      res.status(500).json({ error: err.message });
    }
  }
});

app.listen(PORT, () => {
  console.log(`Aerchain Doc Formatter running on http://localhost:${PORT}`);
});
