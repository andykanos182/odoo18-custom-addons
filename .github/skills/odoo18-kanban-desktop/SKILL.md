---
name: odoo18-kanban-desktop
description: 'Use when creating an advanced desktop or mobile Kanban view in Odoo 18 using OWL, including custom controllers, view switchers, custom fields, and context-based computes.'
argument-hint: 'Target model or module name'
user-invocable: true
disable-model-invocation: false
---

# Odoo 18 Advanced OWL Kanban Customization

## When to Use
- You need to create a custom Kanban view with specialized buttons (e.g., pricelist selectors, category filters) inside the control panel.
- You need inline edit toggles or interactive custom field widgets directly on Kanban cards.
- You want to patch the Control Panel to add new view switcher buttons (e.g., separating standard Kanban from a custom Kanban action).
- You need to dynamically inject context into the search model or ORM calls based on Kanban UI state to drive Python computes.

## Core Architecture Patterns

### 1. Custom Kanban View & Controller
- Inherit `@web/views/kanban/kanban_controller` to manage state (`useState`) and lifecycle hooks (`onWillStart` to fetch initial data).
- Patch the view context and reload data dynamically when state changes:
  ```javascript
  this.model.config.context.your_key = value;
  this.env.searchModel.update({ context: newContext });
  this.model.load();
  ```
- Define and register the view in the `views` registry, inheriting the standard kanban view but using your custom Controller and `buttonTemplate`.

### 2. View Switcher Patching (`web.ControlPanel`)
- Patch `ControlPanel.prototype` to add methods for opening your custom view action (via `actionService.doAction`) and handling navigation.
- Inject your custom view button into `<nav class="o_cp_switch_buttons">` via XML inheritance (`t-inherit="web.ControlPanel"`).
- Handle interceptions if users need to go back to the default view (e.g., listening to `t-on-click.capture` on the switch nav to redirect to native actions).

### 3. Inline Interactive Kanban Fields
- Create custom OWL Components for fields (e.g., toggle badges) inheriting `@odoo/owl` `Component`.
- Make sure to use `standardFieldProps` if needed, but spread them into `props`.
- Use `useService("orm")` and `this.props.record.resModel` / `resId` to perform `write` operations directly from the component.
- Important: Call `await this.props.record.load()` after the write to refresh the UI immediately without a full page reload.
- Register components to the `"fields"` registry.

### 4. Context-Dependent Computed Fields (Backend)
- Use `@api.depends_context('key')` to trigger recomputes when the frontend Controller updates the context.
- Example: computing profit/price dynamically depending on a `pricelist` selected in the custom Kanban buttons.

## Boilerplate Assets

This skill includes boilerplate JS files in the `assets/` folder to quickly bootstrap your modules. Refer to them when writing new code:
- **`assets/kanban_controller.js.template`**: Boilerplate for a KanbanController that injects custom filters into the context.
- **`assets/view_switcher_patch.js.template`**: Boilerplate for patching the `ControlPanel` to handle custom/default view navigation.
- **`assets/inline_toggle_widget.js.template`**: Boilerplate for an interactive field widget that updates records via ORM directly from the UI.

## Advanced Note: Dynamic Action Navigation
When patching `ControlPanel` for view switching, relying on a hardcoded XML-ID (e.g. `module_name.default_action_xml_id`) limits reusability. 
Consider:
- Reading the original `action` from `this.env.config.actionXmlId`.
- Retrieving generic action data via ORM search based on the model.
- If hardcoding is necessary for speed, be explicit in comments that the switcher is scoped to a specific target model (e.g., `product.template`).

## Implementation Steps
1. **Frontend JS**: Create the `KanbanController` and register the `js_class` for the Kanban view.
2. **Frontend UI**: Build the UI template for custom buttons (`t-inherit="web.KanbanView.Buttons"`).
3. **Control Panel**: Build the `ControlPanel` patch (JS and XML) to hook your custom view action into the native switcher.
4. **Custom Widgets**: Implement interactive custom fields for inline edits on cards.
5. **Backend XML**: Create the action window and view records in XML, ensuring `<kanban js_class="your_custom_class">` is used.
6. **Backend Python**: Setup context-dependent fields (`@api.depends_context`) in Python models.
