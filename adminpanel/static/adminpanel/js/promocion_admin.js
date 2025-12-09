(function () {
  function getRow(id) {
    const input = document.getElementById(id);
    if (!input) return null;
    return input.closest('p') || input.parentElement;
  }

  function togglePromoFields() {
    const tipoSelect = document.getElementById("id_tipo");
    if (!tipoSelect) return;

    const pctRow = getRow("id_porcentaje");
    const pct2Row = getRow("id_porcentaje_segunda_unidad");

    const value = tipoSelect.value;

    if (pctRow) pctRow.style.display = "";
    if (pct2Row) pct2Row.style.display = "";

    if (value === "2x1") {
    
      if (pctRow) {
        pctRow.style.display = "none";
        const input = pctRow.querySelector("input");
        if (input) input.value = "";
      }
      if (pct2Row) {
        pct2Row.style.display = "none";
        const input2 = pct2Row.querySelector("input");
        if (input2) input2.value = "";
      }
    } else if (value === "porcentaje") {
      if (pctRow) pctRow.style.display = "";
      if (pct2Row) {
        pct2Row.style.display = "none";
        const input2 = pct2Row.querySelector("input");
        if (input2) input2.value = "";
      }
    } else if (value === "segunda_unidad") {
      if (pctRow) {
        pctRow.style.display = "none";
        const input = pctRow.querySelector("input");
        if (input) input.value = "";
      }
      if (pct2Row) pct2Row.style.display = "";
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    const tipoSelect = document.getElementById("id_tipo");
    if (!tipoSelect) return;

    togglePromoFields();
    tipoSelect.addEventListener("change", togglePromoFields);
  });
})();
