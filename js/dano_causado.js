
function calcular_dano() {
    let dano_dados = document.getElementById('dano_dado').value
    let dano_bonus_arma = document.getElementById('dano_arma').value
    let multiplicador_critico = document.getElementById('critical').value
    let outro_bonus = document.getElementById('outros').value
    let total = document.getElementById('dano_total')

    if (outro_bonus) {
        total.innerHTML = parseFloat((Number(dano_dados) * (Number(dano_bonus_arma) / 100 + 1) * Number(multiplicador_critico) * (Number(outro_bonus) / 100 + 1)).toFixed(2));
    } else {
        total.innerHTML = parseFloat((Number(dano_dados) * (Number(dano_bonus_arma) / 100 + 1) * Number(multiplicador_critico)).toFixed(2));
    }




}