// Text
function bonusMod() {
    //Inputs
    let forca = Number(document.getElementById('in_for').value);
    let destreza = Number(document.getElementById('in_des').value);
    let constituicao = Number(document.getElementById('in_con').value);
    let inteligencia = Number(document.getElementById('in_int').value);
    let sabedoria = Number(document.getElementById('in_sab').value);
    let carisma = Number(document.getElementById('in_car').value);

    //Prints
    let bonusFor = document.getElementById('mod_for');
    let bonusDes = document.getElementById('mod_des');
    let bonusCon = document.getElementById('mod_con');
    let bonusInt = document.getElementById('mod_int');
    let bonusSab = document.getElementById('mod_sab');
    let bonusCar = document.getElementById('mod_car');

    mod_for = generateAtributeMod(forca);
    mod_des = generateAtributeMod(destreza);
    mod_con = generateAtributeMod(constituicao);
    mod_int = generateAtributeMod(inteligencia);
    mod_sab = generateAtributeMod(sabedoria);
    mod_car = generateAtributeMod(carisma);

    let listBruta = [generateAtributeMod(forca), generateAtributeMod(destreza), generateAtributeMod(constituicao), generateAtributeMod(inteligencia), generateAtributeMod(sabedoria), generateAtributeMod(carisma)]
    let bonusList = [];

    for (let i = 0; i < listBruta.length; i++) {
        if (listBruta[i] > 0) {
            bonusList.push("+" + listBruta[i]);
        } else {
            bonusList.push(listBruta[i])
        }
    }

    bonusFor.innerHTML = bonusList[0];
    bonusDes.innerHTML = bonusList[1];
    bonusCon.innerHTML = bonusList[2];
    bonusInt.innerHTML = bonusList[3];
    bonusSab.innerHTML = bonusList[4];
    bonusCar.innerHTML = bonusList[5];



    //utils
}

function generateAtributeMod(valor) {
    let result = Math.floor((valor / 2) - 5);
    return result;
}

function default_onload() {
    let forca = document.getElementById('in_for');
    let destreza = document.getElementById('in_des');
    let constituicao = document.getElementById('in_con');
    let inteligencia = document.getElementById('in_int');
    let sabedoria = document.getElementById('in_sab');
    let carisma = document.getElementById('in_car');

    forca.value = 10;
    destreza.value = 10;
    constituicao.value = 10;
    inteligencia.value = 10;
    sabedoria.value = 10;
    carisma.value = 10;

    bonusMod();
}