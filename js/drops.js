// Lista de objetos JSON

  
// Função para realizar o sorteio
function sortear() {
  // Calcula a soma total das chances
  var somaChances = objetos.reduce(function (total, objeto) {
    return total + objeto.chance;
  }, 0);

  // Gera um número aleatório entre 0 e a soma total das chances
  var numeroSorteado = Math.random() * somaChances;

  // Percorre a lista de objetos e verifica em qual intervalo o número sorteado se encontra
  var acumulado = 0;
  for (var i = 0; i < objetos.length; i++) {
    acumulado += objetos[i].chance;
    if (numeroSorteado < acumulado) {
      return objetos[i]; // Retorna a label do objeto sorteado
    }
  }

  // Caso ocorra algum erro, retorna null
  return null;
}

// Exemplo de uso
for (var i = 0; i < 10; i++) {
  var objetoSorteado = sortear();
  console.log('Objeto sorteado:', objetoSorteado);
}