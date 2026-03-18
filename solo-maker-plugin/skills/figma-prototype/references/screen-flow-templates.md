# Screen Flow Templates

Pre-built prototype flows for common product types. Each template defines required screens, navigation structure, component inventory, and interaction patterns.

---

## Template 1: SaaS Dashboard

**Best for**: B2B SaaS products, analytics platforms, business tools

### Required Screens

| Screen        | Purpose         | Key Components                                                                                               |
| ------------- | --------------- | ------------------------------------------------------------------------------------------------------------ |
| **Login**     | Authentication  | Email input, password input, "Forgot password" link, "Sign in" button                                        |
| **Dashboard** | Main hub        | Header with nav, KPI cards (3-5 metrics), data visualization (chart/graph), recent activity list, CTA button |
| **Settings**  | Configuration   | Sidebar nav, form sections (Profile, Billing, Team, Integrations), save button                               |
| **Profile**   | User management | Avatar upload, name/email fields, password change, notification preferences                                  |

### Navigation Structure

```
Login → Dashboard (home)
  ├─→ Settings
  ├─→ Profile
  └─→ [Feature pages as needed]
```

### Component Inventory

- **Header**: Logo, main nav (Dashboard, Reports, Settings), user avatar dropdown
- **Sidebar**: (Optional) Secondary navigation for feature-heavy apps
- **Cards**: Metric cards with icon, value, trend indicator
- **Tables**: Data tables with sorting, filtering, pagination
- **Forms**: Input fields, dropdowns, checkboxes, save/cancel buttons
- **Modals**: Confirmation dialogs, create/edit forms

### Interaction Patterns

- Click logo → Return to Dashboard
- Click user avatar → Dropdown menu (Profile, Settings, Logout)
- Click metric card → Drill down to detail view
- Click table row → Open detail modal or navigate to detail page

---

## Template 2: Mobile App

**Best for**: Consumer mobile apps, social apps, productivity tools

### Required Screens

| Screen         | Purpose      | Key Components                                                                   |
| -------------- | ------------ | -------------------------------------------------------------------------------- |
| **Splash**     | Brand intro  | Logo, tagline, loading indicator                                                 |
| **Onboarding** | Feature tour | 3-5 slides with image + headline + description, skip/next buttons, progress dots |
| **Home**       | Main feed    | Top nav bar, content cards (infinite scroll), bottom tab bar                     |
| **Detail**     | Item view    | Back button, hero image, title, description, action buttons                      |
| **Profile**    | User account | Avatar, username, stats, settings icon, content grid                             |

### Navigation Structure

```
Splash → Onboarding → Home
  ├─→ Detail (from any card)
  ├─→ Profile (from tab bar)
  └─→ Search/Explore (from tab bar)
```

### Component Inventory

- **Top Nav**: Back button, title, action icon (search, settings, etc.)
- **Bottom Tab Bar**: 4-5 tabs (Home, Search, Create, Notifications, Profile)
- **Cards**: Image thumbnail, title, subtitle, metadata (likes, comments)
- **Buttons**: Primary (solid), secondary (outline), icon buttons
- **Forms**: Mobile-optimized inputs with large touch targets

### Interaction Patterns

- Swipe left/right on onboarding slides
- Tap card → Navigate to Detail
- Tap bottom tab → Switch view
- Pull to refresh on Home feed
- Swipe back to return to previous screen

---

## Template 3: Landing Page

**Best for**: Marketing sites, product launches, lead generation

### Required Screens

| Screen       | Purpose          | Key Components                                                         |
| ------------ | ---------------- | ---------------------------------------------------------------------- |
| **Hero**     | First impression | Headline, subheadline, hero image/video, primary CTA, secondary CTA    |
| **Features** | Value props      | 3-6 feature blocks (icon, title, description), optional screenshot     |
| **Pricing**  | Plans            | 3 pricing tiers (cards with features list, price, CTA button)          |
| **CTA**      | Conversion       | Final headline, email capture form, social proof (logos, testimonials) |

### Navigation Structure

```
Single-page scroll:
Hero → Features → Pricing → CTA

OR multi-page:
Hero (index.html)
  ├─→ Features (features.html)
  ├─→ Pricing (pricing.html)
  └─→ Contact (contact.html)
```

### Component Inventory

- **Header**: Logo, nav links (Features, Pricing, About, Contact), "Get Started" button
- **Hero Section**: H1 headline, paragraph, 2 CTA buttons, hero visual
- **Feature Blocks**: Icon, H3 title, paragraph description
- **Pricing Cards**: Plan name, price, feature list (checkmarks), CTA button
- **Footer**: Links, social icons, copyright

### Interaction Patterns

- Click nav link → Smooth scroll to section (single-page) or navigate (multi-page)
- Click CTA → Open signup modal or navigate to signup page
- Hover pricing card → Highlight/scale effect

---

## Template 4: E-commerce

**Best for**: Online stores, product catalogs, checkout flows

### Required Screens

| Screen             | Purpose        | Key Components                                                                                               |
| ------------------ | -------------- | ------------------------------------------------------------------------------------------------------------ |
| **Product List**   | Browse catalog | Header with search, filter sidebar, product grid (image, title, price, "Add to cart"), pagination            |
| **Product Detail** | Item view      | Image gallery, title, price, description, size/color selector, quantity input, "Add to cart" button, reviews |
| **Cart**           | Review order   | Cart items list (image, title, quantity, price, remove), subtotal, "Checkout" button                         |
| **Checkout**       | Purchase       | Shipping form, payment form, order summary, "Place order" button                                             |

### Navigation Structure

```
Product List → Product Detail → Cart → Checkout
  ↑              ↑
  └──────────────┘ (Continue shopping)
```

### Component Inventory

- **Header**: Logo, search bar, cart icon (with item count badge)
- **Product Card**: Image, title, price, "Quick add" button
- **Product Gallery**: Main image + thumbnail strip
- **Filters**: Checkboxes (category, price range, brand), "Apply" button
- **Cart Item**: Thumbnail, title, quantity stepper, price, remove icon
- **Forms**: Shipping address, payment details (card number, expiry, CVV)

### Interaction Patterns

- Click product card → Navigate to Product Detail
- Click "Add to cart" → Update cart count, show toast notification
- Click cart icon → Navigate to Cart
- Click thumbnail → Update main product image
- Adjust quantity → Update subtotal in real-time

---

## Template 5: Admin Panel

**Best for**: Internal tools, CMS, data management systems

### Required Screens

| Screen         | Purpose        | Key Components                                                                                                        |
| -------------- | -------------- | --------------------------------------------------------------------------------------------------------------------- |
| **Login**      | Authentication | Email, password, "Sign in" button                                                                                     |
| **Table View** | Data list      | Sidebar nav, data table (columns: ID, Name, Status, Date, Actions), search bar, filter dropdowns, "Create new" button |
| **Form**       | Create/Edit    | Breadcrumb nav, form fields (text, dropdown, date picker, file upload), "Save" and "Cancel" buttons                   |
| **Analytics**  | Insights       | KPI cards, charts (line, bar, pie), date range picker, export button                                                  |

### Navigation Structure

```
Login → Table View (default)
  ├─→ Form (create/edit)
  ├─→ Analytics
  └─→ Settings
```

### Component Inventory

- **Sidebar**: Logo, nav links (Dashboard, Users, Content, Settings), collapse toggle
- **Top Bar**: Breadcrumb, search, notifications, user avatar
- **Data Table**: Sortable columns, row actions (edit, delete), bulk select
- **Forms**: Label + input pairs, validation messages, save/cancel buttons
- **Charts**: Line chart (trends), bar chart (comparisons), pie chart (distribution)

### Interaction Patterns

- Click sidebar link → Navigate to section
- Click table row → Navigate to detail/edit form
- Click "Create new" → Navigate to blank form
- Click column header → Sort table
- Click "Save" → Validate form, show success message, return to table

---

## Using Templates

### 1. Select Template

Based on PRD analysis:

```python
if "dashboard" in prd or "analytics" in prd:
    template = "SaaS Dashboard"
elif "mobile" in prd or "app" in prd:
    template = "Mobile App"
elif "landing" in prd or "marketing" in prd:
    template = "Landing Page"
elif "store" in prd or "shop" in prd or "product" in prd:
    template = "E-commerce"
elif "admin" in prd or "cms" in prd or "internal" in prd:
    template = "Admin Panel"
else:
    template = "SaaS Dashboard"  # Default fallback
```

### 2. Customize Screens

Adapt template screens to user stories:

- Add screens for unique features (e.g., "Reports" screen for SaaS Dashboard)
- Remove screens not needed (e.g., skip Onboarding for Mobile App if not required)
- Merge screens if functionality overlaps

### 3. Apply Design Tokens

Use `design-tokens.json` to style all components consistently:

- Primary color → CTA buttons, active nav items, links
- Accent color → Badges, success states, highlights
- Font family → All text elements
- Spacing unit → Margins, padding, gaps

### 4. Validate Coverage

Check that all user stories have corresponding screens:

```python
for story in user_stories:
    if story not in template_screens:
        flag_missing_screen(story)
```
