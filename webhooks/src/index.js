export default {
  async fetch(request, env, ctx) {
    // Only accept POST requests for a webhook
    if (request.method !== "POST") {
      return new Response("Method Not Allowed", { status: 405 });
    }

    try {
      // Parse the JSON payload
      const payload = await request.json();
      
      console.log("Received webhook payload:", payload);

      // Add your webhook processing logic here

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
