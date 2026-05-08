/*
 * Add a small title-case helper button to Product Template name fields.
 * Works for the main product.template form name field and translated name textareas.
 */
function andykanozProductTitlecase(rawValue) {
    if (!rawValue || !rawValue.trim()) {
        return rawValue;
    }
    return rawValue
        .split(/(\s+)/)
        .map((part) => {
            if (/^\s+$/.test(part)) {
                return part;
            }
            return part.charAt(0).toUpperCase() + part.slice(1).toLowerCase();
        })
        .join("");
}

function andykanozDispatchInputEvents(el) {
    el.dispatchEvent(new Event('input', { bubbles: true, cancelable: true }));
    el.dispatchEvent(new Event('change', { bubbles: true, cancelable: true }));
}

function andykanozFindFieldForButton(button, field) {
    const sibling = button.previousElementSibling;
    if (sibling && (sibling.tagName === 'TEXTAREA' || sibling.tagName === 'INPUT')) {
        return sibling;
    }
    const translateWrapper = field.closest('.o_field_translate');
    if (translateWrapper) {
        const candidate = translateWrapper.querySelector('textarea[id^="name_"], input[id^="name_"], textarea[name="name"], input[name="name"]');
        if (candidate) {
            return candidate;
        }
    }
    if (field && document.contains(field)) {
        return field;
    }
    const fallback = button.parentElement?.querySelector('textarea[id^="name_"], input[id^="name_"], textarea[name="name"], input[name="name"]');
    return fallback || field;
}

function andykanozCreateTitlecaseButton(field) {
    if (field.dataset.andykanozTitlecaseAttached) {
        return;
    }
    field.dataset.andykanozTitlecaseAttached = '1';

    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-outline-secondary o_pc_titlecase_btn';
    button.title = "Convert to Title Case (e.g. 'andyka noz' → 'Andyka Noz')";
    button.innerHTML = '<i class="fa fa-font"></i>';
    button.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        const targetField = andykanozFindFieldForButton(button, field);
        if (!targetField) {
            return;
        }
        const raw = targetField.value || '';
        const titled = andykanozProductTitlecase(raw);
        if (titled && titled !== raw) {
            targetField.value = titled;
            targetField.setAttribute('value', titled);
            andykanozDispatchInputEvents(targetField);
            targetField.blur();
            targetField.focus();
        }
    });

    const createFormGroup = field.closest('.o_pc_name_input_group');
    if (createFormGroup) {
        createFormGroup.insertBefore(button, field);
        return;
    }

    const titleRow = field.closest('.oe_title .d-flex');
    if (titleRow) {
        button.style.position = 'static';
        button.style.marginLeft = '0.5rem';
        titleRow.appendChild(button);
        return;
    }

    const translateWrapper = field.closest('.o_field_translate');
    const wrapper = translateWrapper && translateWrapper !== field ? translateWrapper : field.parentElement;
    if (wrapper && wrapper.classList.contains('o_field_translate')) {
        wrapper.style.position = 'relative';
        button.style.position = 'absolute';
        button.style.top = '8px';
        button.style.right = '60px';
        button.style.zIndex = '1';
        wrapper.appendChild(button);
        return;
    }

    field.insertAdjacentElement('afterend', button);
}

function andykanozAttachTitlecaseButtons(root) {
    if (!root) {
        return;
    }

    const fieldSelectors = [
        '.o_form_view[data-model="product.template"] .oe_title .d-flex input[name="name"]',
        '.o_form_view[data-model="product.template"] .oe_title .d-flex textarea[name="name"]',
        '.oe_title .d-flex input[name="name"]',
        '.oe_title .d-flex textarea[name="name"]',
        'textarea.o_field_translate[id^="name_"]',
        'input.o_field_translate[id^="name_"]',
    ];

    fieldSelectors.forEach((selector) => {
        root.querySelectorAll(selector).forEach((field) => {
            andykanozCreateTitlecaseButton(field);
        });
    });
}

function andykanozInitializeTitlecaseButtons() {
    andykanozAttachTitlecaseButtons(document);

    const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
            if (mutation.type === 'childList' && mutation.addedNodes.length > 0) {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType !== Node.ELEMENT_NODE) {
                        return;
                    }
                    andykanozAttachTitlecaseButtons(node);
                });
            }
        });
    });

    observer.observe(document.body, {
        childList: true,
        subtree: true,
    });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', andykanozInitializeTitlecaseButtons);
} else {
    andykanozInitializeTitlecaseButtons();
}
