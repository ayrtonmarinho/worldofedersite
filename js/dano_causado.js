
function calcular_dano() {
    let dano_dados = document.getElementById('dano_dado').value
    let dano_bonus_arma = document.getElementById('dano_arma').value
    let todos_bonus = dano_bonus_arma.split(',');
    let multiplicador_critico = document.getElementById('critical').value
    let total = document.getElementById('dano_total')
    let base_vida = Number(document.getElementById('t_hp').value)
    let percent = Number(document.getElementById('dano_hp').value)

    if (percent >= 1) {
        total.innerHTML = Math.ceil(calculaBonus(todos_bonus, dano_dados) * Number(multiplicador_critico)+calcularBaseVida(base_vida, percent));
    } else {
        total.innerHTML = Math.ceil(calculaBonus(todos_bonus, dano_dados) * Number(multiplicador_critico));
    }
 
    



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

function calcularBaseVida(vida, percent) {
    return vida * (percent / 100);
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
