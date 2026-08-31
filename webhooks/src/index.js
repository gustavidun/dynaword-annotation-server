export default {
  async fetch(request, env, ctx) {
    // ----------------------------------------------------
    // ROUTE 1: GET (used to poll pending tasks)
    // ----------------------------------------------------
    if (request.method === "GET") {
      if (request.headers.get("X-Webhook-Secret") !== env.WEBHOOK_SECRET) {
        return new Response("Unauthorized", { status: 401 });
      }

      try {
        // Fetch up to 50 pending webhooks
        const { results } = await env.dynaword_webhooks.prepare(
          "SELECT * FROM webhooks WHERE status = 'pending' ORDER BY created_at ASC LIMIT 50"
        ).all();

        return new Response(JSON.stringify(results), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      } catch (error) {
        console.error("Database read error:", error);
        return new Response("Internal Server Error", { status: 500 });
      }
    }

    // ----------------------------------------------------
    // ROUTE 2: POST (HF webhook)
    // ----------------------------------------------------
    if (request.method === "POST") {
      if (request.headers.get("X-Webhook-Secret") !== env.WEBHOOK_SECRET) {
        return new Response("Unauthorized", { status: 401 });
      }

      try {
        const payload = await request.json();
        console.log("Received webhook payload:", payload);

        // store in D1 database
        await env.dynaword_webhooks.prepare(
          "INSERT INTO webhooks (payload, created_at, status) VALUES (?, ?, ?)"
        ).bind(JSON.stringify(payload), new Date().toISOString(), 'pending').run();

        return new Response(JSON.stringify({ success: true }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        });
      } catch (error) {
        console.error("Failed to parse webhook:", error);
        return new Response("Bad Request", { status: 400 });
      }
    }

    // ----------------------------------------------------
    // ROUTE 3: PATCH (mark task as completed)
    // ----------------------------------------------------
    if (request.method === "PATCH") {
      if (request.headers.get("X-Webhook-Secret") !== env.WEBHOOK_SECRET) {
        return new Response("Unauthorized", { status: 401 });
      }

      try {
        const body = await request.json();
        // Expecting { ids: [1, 2, 3] }
        if (!body.ids || !Array.isArray(body.ids) || body.ids.length === 0) {
          return new Response("Bad Request: missing ids array", { status: 400 });
        }

        const placeholders = body.ids.map(() => "?").join(",");
        await env.dynaword_webhooks.prepare(
          `UPDATE webhooks SET status = 'completed' WHERE id IN (${placeholders})`
        ).bind(...body.ids).run();

        return new Response(JSON.stringify({ success: true }), { status: 200 });
      } catch (error) {
        console.error("Update error:", error);
        return new Response("Internal Server Error", { status: 500 });
      }
    }

    // If it's not GET, POST, or PATCH
    return new Response("Method Not Allowed", { status: 405 });
  },

  // ----------------------------------------------------
  // CRON TRIGGER: Cleans up the database automatically
  // ----------------------------------------------------
  async scheduled(event, env, ctx) {
    console.log("Running scheduled database cleanup...");
    try {
      // Delete rows that are older than 7 days
      await env.dynaword_webhooks.prepare(
        "DELETE FROM webhooks WHERE created_at < datetime('now', '-7 days')"
      ).run();
      console.log("Cleanup successful.");
    } catch (error) {
      console.error("Failed to run scheduled cleanup:", error);
    }
  },
};
