# The Professional Prototyping Kit: Solo Edition

This kit provides a high-fidelity HTML/CSS boilerplate for rapid, standalone prototyping. It is designed to mimic modern SaaS aesthetics (Glassmorphism, Inter typography, and subtle micro-animations) without requiring a build step.

---

## 1. Professional Boilerplate (Save as `prototype.html`)

```html
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Solo OS Prototype</title>
    <!-- Modern Typography -->
    <link
      href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&display=swap"
      rel="stylesheet"
    />
    <style>
      :root {
        --bg-blur: rgba(255, 255, 255, 0.7);
        --primary: #6366f1; /* Indigo */
        --primary-glow: rgba(99, 102, 241, 0.4);
        --glass-border: rgba(255, 255, 255, 0.3);
        --text-main: #1e293b;
        --text-muted: #64748b;
      }

      * {
        box-sizing: border-box;
      }
      body {
        font-family: "Inter", sans-serif;
        background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        color: var(--text-main);
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 0;
        padding: 20px;
      }

      /* Glassmorphism Card */
      .card {
        background: var(--bg-blur);
        backdrop-filter: blur(12px);
        -webkit-backdrop-filter: blur(12px);
        border: 1px solid var(--glass-border);
        border-radius: 24px;
        padding: 40px;
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.05);
        max-width: 480px;
        width: 100%;
        text-align: center;
        transition: transform 0.3s ease;
      }

      .card:hover {
        transform: translateY(-5px);
      }

      h1 {
        font-size: 28px;
        font-weight: 700;
        margin-bottom: 8px;
      }
      p {
        color: var(--text-muted);
        margin-bottom: 32px;
        line-height: 1.6;
      }

      /* Professional Inputs */
      input {
        width: 100%;
        padding: 14px 20px;
        border-radius: 12px;
        border: 1px solid #cbd5e1;
        background: white;
        font-size: 16px;
        margin-bottom: 16px;
        transition: all 0.2s ease;
      }

      input:focus {
        outline: none;
        border-color: var(--primary);
        box-shadow: 0 0 0 4px var(--primary-glow);
      }

      /* Primary Action Button */
      .btn {
        background: var(--primary);
        color: white;
        border: none;
        padding: 16px;
        width: 100%;
        border-radius: 12px;
        font-size: 16px;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
        box-shadow: 0 4px 12px var(--primary-glow);
      }

      .btn:hover {
        background: #4f46e5;
        transform: scale(1.02);
      }
      .btn:active {
        transform: scale(0.98);
      }

      /* Loading Spinner */
      .spinner {
        border: 4px solid rgba(0, 0, 0, 0.1);
        width: 36px;
        height: 36px;
        border-radius: 50%;
        border-left-color: var(--primary);
        animation: spin 1s linear infinite;
        display: none;
        margin: 20px auto;
      }

      @keyframes spin {
        0% {
          transform: rotate(0deg);
        }
        100% {
          transform: rotate(360deg);
        }
      }
    </style>
  </head>
  <body>
    <div class="card" id="main-content">
      <h1>[Feature Name]</h1>
      <p>[Strategic Aha! Moment Description]</p>
      <input type="text" placeholder="[Attribute 1, e.g. Email]" />
      <button class="btn" onclick="simulateAction()">[Primary Action]</button>
      <div class="spinner" id="loader"></div>
    </div>

    <script>
      function simulateAction() {
        document.querySelector(".btn").style.display = "none";
        document.querySelector("#loader").style.display = "block";
        setTimeout(() => {
          document.getElementById("main-content").innerHTML = `
                    <h1 style="color: #059669">Success!</h1>
                    <p>The [Value Proposition] has been validated. Check your dashboard.</p>
                    <button class="btn" onclick="location.reload()">Reset Prototype</button>
                `;
        }, 1500);
      }
    </script>
  </body>
</html>
```

---

## 2. Design Token Framework (Solo Standard)

When customizing the boilerplate, follow these "Solo Premium" constraints:

- **Typography**: Always use `Inter` or `Outfit` for body text. 16px minimum.
- **Spacing**: Use a 4px grid (4, 8, 16, 24, 32, 40, 64).
- **Colors**: Never use pure blacks (`#000`). Use slates (`#1e293b`) or dark indigos.
- **Micro-interactions**: Every button must have a `:hover` and `:active` state.

---

## 3. Prototyping Strategy: The "Fake Door" Protocol

Use this boilerplate to test **Desirability** before you build.

1.  Map the solution to the [OST Worksheet](../references/worksheet.md).
2.  Deploy the prototype (e.g., via GitHub Pages or local preview).
3.  Send the link to 3 target users from your `proto-persona` database.
4.  Record the "Time to Click" and any friction points.

---

## 4. Integration with Other Skills

- **PRD**: Embed the screenshot of your validated prototype in the "UX" section of `prd-development.md`.
- **Validation**: Save results from this prototype in `validation-checkpoint.md`.
