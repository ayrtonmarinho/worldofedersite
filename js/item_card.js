function salvarDivComoPNG() {
  card = document.getElementById('weapon_card');
  card.addEventListener('click', function () {
    alertify.confirm('Salvar Card', 'Deseja salvar o item como PNG.', function () {
      var div = document.getElementById("weapon_card");
      var scale = 1.25; // Aumentar a escala por 2 (pode ajustar conforme necessário)
    
      // Definir a largura e a altura da div com base na escala
      div.style.width = div.offsetWidth * scale + "px";
      div.style.height = div.offsetHeight * scale + "px";
    
      html2canvas(div, { scale: scale }).then(function(canvas) {
        var img = canvas.toDataURL("image/png");
        var link = document.createElement('a');
        link.href = img;
        link.download = 'div_imagem.png';
        link.click();
    
        // Redefinir a largura e a altura da div para o valor original
        div.style.width = "";
        div.style.height = "";
      });
    }
        , function () { alertify.error('Cancelado!') });
});
}

function gen_weapon() {
  
}