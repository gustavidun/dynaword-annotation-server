export default {
  async fetch(request, env, ctx) {

    // webhooks are always POST requests
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }
    // verify HF secret
    if (request.headers.get("X-Webhook-Secret") !== env.WEBHOOK_SECRET) {
      return new Response("Unauthorized", { status: 401 });
    }

    try {
      const payload = await request.json();
      console.log("Received webhook payload:", payload);

      // store in D1 database
      await env.dynaword_webhooks.prepare(
        "INSERT INTO webhooks (payload, created_at, status) VALUES (?, ?, ?)"
      )
        .bind(JSON.stringify(payload), new Date().toISOString(), 'pending')
        .run();


      return new Response(JSON.stringify({ success: true }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      });
    } catch (error) {
      console.error("Failed to parse webhook:", error);
      return new Response("Bad Request", { status: 400 });
    }
  },
};
