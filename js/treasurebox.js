var evento1 = ['<p class="raro">Esfera do Fogo</p>(10)', '<p class="raro">Esfera do Água</p>(10)', '<p class="raro">Esfera do Ar</p>(10)'];
var dinheiro = ['<p class="comum">Ouro</p> (100)', '<p class="comum">Ouro</p> (250)']

function rarity(item) {
    if (item == '2') {
        return '<p class="raro">'
    } else if (item == '3') {
        return '<p class="exotico">'
    } else if (item == '4') {
        return '<p class="lendario">'
    } else if (item == '5') {
        return '<p class="mitico">'
    } else if (item == '6') {
        return '<p class="eternal">'
    } else {
        return '<p class="comum">'
    }

}

//name, rarity, dropchance, qtd
function getTreasure() {
    let treasureList = document.getElementById('boxcontent').value;
    let rangeItens = itemQuantity(1, 6);
    let lista = treasureList.split('\n');
    lootbox = itens(lista, 4)
    //console.log(lista);
    console.log(lootbox)
    screenShow(lootbox);


}

function screenShow(lootbox) {
    psize = lootbox.length;
    let printer;
    let mark = document.getElementById('tesouros')
    for (i = 0; i < psize; i++) {
        printer = lootbox[i];
        mark.insertAdjacentHTML('afterend', printer);
    }
}

function itens(lista, rangeItens) {
    let max = lista.length;
    let n = rangeItens;
    let lootbox = [];
    console.log(lista);
    for (i = 0; i < n; i++) {
        let valor = Math.trunc(Math.random() * (1 - 101) * -1);
        console.log(valor);
        if (valor <= max) {
            lootbox.push(lista[valor]);
        } else {
            let ordinaryDrop = Math.trunc(Math.random() * (1 - (evento1.length + 1)) * -1);
            //console.log(ordinaryDrop)
            lootbox.push(evento1[ordinaryDrop]);
        }
    }
    return lootbox;
}



function itemQuantity(min, max) {
    let qtd = Math.trunc(Math.random() * (max - min));
    return qtd;
}