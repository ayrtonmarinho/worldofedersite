
function calcular_dano() {
    let dano_dados = document.getElementById('dano_dado').value
    let dano_bonus_arma = document.getElementById('dano_arma').value
    let todos_bonus = dano_bonus_arma.split(',');
    let multiplicador_critico = document.getElementById('critical').value
    let total = document.getElementById('dano_total')

    
 
    total.innerHTML = Math.ceil(calculaBonus(todos_bonus, dano_dados) * Number(multiplicador_critico));



}

function calculaBonus(vetor, dano_dados) {
    let vetorNumeros = textToNumberArray(vetor);
    console.log(vetorNumeros);
    let total_dano = dano_dados;
    let tam = vetorNumeros.length;
    for (let i = 0; i < tam; i++ ){
        total_dano = total_dano * numMult(vetorNumeros[i]);
    }
    return total_dano;
}

function numMult(numero) {
    if (numero > 0) {
        return (numero / 100 + 1);
    }
    return 1;
    
}

function textToNumberArray(vetor) {
    let tam = vetor.length;
    for (let i = 0; i < tam; i++){
        vetor[i] = Number(vetor[i]);
    }
    return vetor;
}
