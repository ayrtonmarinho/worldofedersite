var acertos
var criticos
var criticalDam
var dano
var b_dano


var dmg
var multiplicador
var total_dmg

function calcular() {
    dmg = []
    total_dmg = 0
    multiplicador = 1

    acertos = document.getElementById('acertos').value
    criticos = document.getElementById('criticos').value
    criticalDam = document.getElementById('crtDMG').value
    dano = document.getElementById('dano').value
    b_dano = document.getElementById('bDano').value

    if (b_dano == 0) {
        b_dano = 1
    }

    console.log(b_dano)

    if (acertos == "" || criticos == "" || criticalDam == "" || dano == "") {
        window.alert('Algum campo esta vazio. Corrija!')
    } else {
        critical = criticos.split(',')
        console.log(critical)
        for (let i = 0; i < acertos; i++) {
            dmg[i] = dano * multiplicador
            multiplicador += 0.15
            dmg[i] = Math.ceil(dmg[i])
        }

        if (critical) {
            for (let i = 0; i < critical.length; i++) {
                crtDmg = critical[i]
                dmg[crtDmg - 1] *= criticalDam
                dmg[crtDmg - 1] = Math.ceil(dmg[crtDmg - 1])
            }
        }

        for (let i = 0; i < acertos; i++) {
            total_dmg += dmg[i]
        }
        var bonus_dmg = (b_dano / 100) + 1
        var bonusfinal = bonus_dmg * total_dmg

        total_dmg = bonusfinal

        document.getElementById('seqDmg').innerHTML = dmg
        document.getElementById('totalDmg').innerHTML = total_dmg

        clearFields()
    }


}

function clearFields() {
    acertos = document.getElementById('acertos').value = ""
    criticos = document.getElementById('criticos').value = ""
    criticalDam = document.getElementById('crtDMG').value = ""
    dano = document.getElementById('dano').value = ""
}

function clearResults() {
    document.getElementById('seqDmg').innerHTML = ""
    document.getElementById('totalDmg').innerHTML = ""
}

function clearIput() {
    criticos = document.getElementById('criticos').value = ""
}

