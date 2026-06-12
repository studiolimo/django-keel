import htmx from 'htmx.org';
import Alpine from 'alpinejs';
import collapse from '@alpinejs/collapse';
import focus from '@alpinejs/focus';

window.htmx = htmx;
window.Alpine = Alpine;
Alpine.plugin(collapse);
Alpine.plugin(focus);

// Selezione righe nelle liste (checkbox + azioni bulk con select-across stile admin).
// Usato da templates/dashboard/ui/list.html e da TableMultiSelectMixin.
Alpine.data('tableSelection', (totalCount) => ({
  numSelected: 0,
  selectAll: false,
  selectAcross: 0,
  selectedAction: '',

  rows() {
    return Array.from(this.$root.querySelectorAll('input[name="selection"]'));
  },
  toggleAll(checked) {
    this.rows().forEach((cb) => (cb.checked = checked));
    this.selectAll = checked;
    this.selectAcross = 0;
    this.recount();
  },
  recount() {
    this.numSelected = this.selectAcross
      ? totalCount
      : this.rows().filter((cb) => cb.checked).length;
  },
  extendToAll() {
    this.selectAcross = 1;
    this.numSelected = totalCount;
  },
  clearSelection() {
    this.rows().forEach((cb) => (cb.checked = false));
    this.selectAll = false;
    this.selectAcross = 0;
    this.numSelected = 0;
  },
}));

// Dialog di conferma per azioni distruttive (sostituisce sweetalert).
Alpine.store('confirm', {
  open: false,
  message: '',
  href: null,
  redirectUrl: null,
  ask(message, href, redirectUrl = null) {
    if (!href) {
      console.warn('[confirm] ask() chiamato senza href: ignorato');
      return;
    }
    this.message = message;
    this.href = href;
    this.redirectUrl = redirectUrl;
    this.open = true;
  },
  proceed() {
    if (this.href) {
      const form = document.getElementById('confirm-form');
      if (form) {
        form.action = this.href;
        if (this.redirectUrl) {
          const input = document.createElement('input');
          input.type = 'hidden';
          input.name = 'redirect_url';
          input.value = this.redirectUrl;
          form.appendChild(input);
        }
        form.submit();
      } else {
        console.warn('[confirm] #confirm-form non trovato: impossibile procedere');
      }
    }
    this.open = false;
  },
  cancel() {
    this.open = false;
  },
});

Alpine.start();
