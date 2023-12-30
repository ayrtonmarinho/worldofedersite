
function onload() {
    
}


function convertToNumberArray() {
    let textContent = document.getElementById('vetor_vida').value;
    //console.log(textContent);
    let vetor = textContent.split(',');
    vetor = vetor.filter(function (i) {
        return i;
    });
    //console.log(vetor);
    tam = vetor.length;
    let numberArray = [];
    for (let i = 0; i < tam; i++){
        numberArray.push(parseInt(vetor[i]));
    }
    //console.log(tam);
    console.log(numberArray);
    return numberArray;
}

function setLevel() {
    let vetor = convertToNumberArray();
    let nivel = vetor.length;
    document.getElementById('nivel').innerHTML = nivel;
    displayAdds(nivel);
}

function displayAdds(nivel) {
    let nv3 = document.getElementById('nv3dice');
    let nv7 = document.getElementById('nv7dice');
    let nv11 = document.getElementById('nv11dice');
    let nv16 = document.getElementById('nv16dice');
    let tTalent = document.getElementById('tTalent');
    let escolha_18 = document.getElementById('escolha_18');

    if (nivel >= 3 & nivel < 7) {
        nv3.style.display = "block";
        nv7.style.display = "none";
        nv11.style.display = "none";
        nv16.style.display = "none";
        tTalent.style.display = "none";
        escolha_18.style.display = "none";
    } else if (nivel >= 7 & nivel < 11) {
        nv3.style.display = "block";
        nv7.style.display = "block";
        nv11.style.display = "none";
        nv16.style.display = "none";
        tTalent.style.display = "none";
        escolha_18.style.display = "none";
    } else if (nivel >= 11 & nivel < 16) {
        nv3.style.display = "block";
        nv7.style.display = "block";
        nv11.style.display = "block";
        nv16.style.display = "none";
        tTalent.style.display = "none";
        escolha_18.style.display = "none";
    } else if (nivel >= 16 & nivel < 17) {
        nv3.style.display = "block";
        nv7.style.display = "block";
        nv11.style.display = "block";
        nv16.style.display = "block";
        tTalent.style.display = "none";
        escolha_18.style.display = "none";
    } else if (nivel >= 17 & nivel < 18) {
        nv3.style.display = "block";
        nv7.style.display = "block";
        nv11.style.display = "block";
        nv16.style.display = "block";
        tTalent.style.display = "block";
        escolha_18.style.display = "none";
    } else if (nivel >= 18) {
        nv3.style.display = "block";
        nv7.style.display = "block";
        nv11.style.display = "block";
        nv16.style.display = "block";
        tTalent.style.display = "block";
        escolha_18.style.display = "block";
    } else {
        nv3.style.display = "none";
        nv7.style.display = "none";
        nv11.style.display = "none";
        nv16.style.display = "none";
        tTalent.style.display = "none";
        escolha_18.style.display = "none";
    }
}

function sumOfLifeBonus(nivel, vetor) {
    let nv3 = document.getElementById('nv3dice');
    let nv7 = document.getElementById('nv7dice');
    let nv11 = document.getElementById('nv11dice');
    let nv16 = document.getElementById('nv16dice');
    let tTalent = document.getElementById('tTalent');
    let escolha_18 = document.getElementById('escolha_18');
}

function gerarVida() {
    let max_hp = 0;
    let hp_bonus_18 = 0;
    let vetor_vida = convertToNumberArray();
    vetor_vida = sumValorArreyPosition(vetor_vida, getConMod());
    let nivel = document.getElementById('nivel').innerText;
    let dureza_r1 = document.getElementById('dureza');
    let hit_dice = parseInt(document.getElementById('hit_dice').value);
    let dureza = false;
    let is_tank = false;
    if (dureza_r1.checked) {
        dureza = true;
    }
    console.log(nivel);
    if (nivel >= 3) {
        let nv3 = document.getElementById('nv3hpdice').value;
        vetor_vida[2] = vetor_vida[2] + parseInt(nv3);
    }
    
    if (nivel >= 7) {
        let nv7 = document.getElementById('nv7hpdice').value;
        vetor_vida[6] = vetor_vida[6] + parseInt(nv7);
    }
    if (nivel >= 11) {
        let nv11 = document.getElementById('nv11hpdice').value;
        vetor_vida[10] = vetor_vida[10] + parseInt(nv11);
    }
    if (nivel >= 16) {
        let nv16 = document.getElementById('nv20hpdice').value;
        vetor_vida[15] = vetor_vida[15] + parseInt(nv16);
    }

    if (nivel >= 17) {
        let tTalent = document.getElementById('tank_talent');
        if (tTalent.checked) {
            is_tank = true;
        }
       
    }
    if (nivel >= 18) {
        //let escolha_18 = document.getElementById('escolha_18');
        const radioButton = document.querySelector('input[type="radio"]:checked');
        hp_bonus_18 = parseInt(radioButton.value);
        
    }

    max_hp = normalize_hp(vetor_vida, is_tank, hp_bonus_18, dureza, hit_dice);
    console.log(max_hp);
    vidaTotal(max_hp);


    
}

function hpBonus(vida_total) {
    return (5 + Math.round(vida_total * 0.15));
}

function somaArray(vetor, limite) {
    let soma = 0;
    for (let i = 0; i < limite; i++){
        soma += vetor[i];
    }
}

function nullAlert(valor) {
    if (valor == null | valor == '') {
        window.alert('algum campo está em branco');
    }
}

function sumValorArreyPosition(array, valor) {
    let t = array.length;
    for (let i = 0; i < t; i++){
        array[i] = array[i]+valor;
    }
    return array;
}

function getConMod() {
    let con = parseInt(document.getElementById('con').value);
    let mod = Math.floor(con / 2 - 5);
    return mod;
}

function normalize_hp(vetor, isTank, bonusHp, dureza, hit_dice) {
    let hp_by_level = [];
    let tam = vetor.length;
    let soma = 0;
    for (let i = 0; i < tam; i++){
        
        if (i == 0) {
            soma = parseInt(vetor[i]);
        } else {
            soma += parseInt(vetor[i]);
            if (i == 4 | i == 9) {
                soma += hit_dice;
            }
            if (i == 14) {
                soma += 2 * hit_dice;
            }
            if (i == 12) {
                soma = soma * 1.25;
            }
            if (i == 16 & isTank) {
                soma = soma * 1.35; 
            }
            if (i == 17) {
                soma += bonusHp;
            }
            if (i == 19) {
                soma = soma * 6;
            }
            if (dureza) {
                soma = terraformar(soma, i + 1);
            }
        }
        console.log(soma)
        hp_by_level.push(soma);
    }
    return hp_by_level;
}

function terraformar(valor, nivel) {
    if (nivel == 3 | nivel == 6 | nivel == 9 | nivel == 12 | nivel == 15 | nivel == 19) {
        return (valor + hpBonus(valor));
    }
    return valor;
}

function vidaTotal(vida_maxima) {
    const vidaMaxima = document.getElementById("vida_total");

    vidaMaxima.innerHTML = Math.round(vida_maxima[vida_maxima.length-1]);
    vidaMaxima.style.display = 'block';
}