
$('#enviarFiltros').click(function(){
      arrayValores = $('#filterAulas').serialize();
      $.ajax({
      url: "/showReservar",
      trditional: "true",
      contentType: 'application/json;charset=utf-8',
      dataType: "json",
      type: "POST",
      data: JSON.stringify({capacidad: arrayValores['capacidad']})
      // success: window.open('reservar', '_blank')
    });
});
