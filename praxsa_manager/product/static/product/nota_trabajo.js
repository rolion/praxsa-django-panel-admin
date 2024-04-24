jQuery(function($){

    let proforma_id = 0

    function can_edit_nota_venta(){
        proforma = $('#id_proforma')
        return proforma.length > 0
    }
    
    function get_proforma(){
        if (can_edit_nota_venta()){
            proforma = $('#id_proforma')
        } else{
            proforma = $('#nota_trabajo_form > div > fieldset:nth-child(1) > div.form-row.field-proforma > div > div > div > a')
            proforma = proforma[0]
            // console.log('selector ', proforma.text)
        }
        return proforma
    }
    // get_proforma_id()
    
    function getProformaCarInfo(proforma_id){
        if(!isNaN(proforma_id)){
            $.ajax({
                url: '/product/get_proforma_car_part_info/'+proforma_id,
                type:"GET",
                success: function(result) {
                    if(result.items.length > 0 ){
                        let rows = ''
                        $.each(result.items, function(key, item){
                            rows+= `
                                    <tr class="form-row has_original dynamic-items" id="">
                                        
                                        <td class="field-width">
                                            <p>${item.name}</p>
                                        </td>
                                        
                                        <td class="field-length">
                                            <p>${item.width}</p>
                                        </td>
                                        <td class="field-length">
                                            <p>${item.length}</p>
                                        </td>
                                        <td class="field-length">
                                            <p>${item.quantity}</p>
                                        </td>
                                    </tr>
                            `
                        })
                        let container = `
                        <br>
                        <div id="model-item-helper" class="tabular inline-related last-related">
                            <fieldset class="module ">
                                <h2></h2>
                                <table>
                                    <thead>
                                        <tr>
                                            <th class="column-width">Item</th>
                                            <th class="column-width">Ancho</th>
                                            <th class="column-length">Largo</th>
                                            <th class="column-length">Cantidad</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                    ${rows}
                                    </tbody>
                                </table>
                            </fieldset>
                        </div>`
                        $('#model-item-helper').remove()
                        $('#detalle_trabajo-group').append(container)
                    }
                }
            })
        }
    }
    function init(){
        if (can_edit_nota_venta()){
            get_proforma().change(function(e){
                proforma_id = $(this).val()
                console.log(proforma_id)
                getProformaCarInfo(proforma_id)
            })
        }else{
            let element_text = get_proforma().text
            proforma_id = element_text.split(' ')[1]
            getProformaCarInfo(proforma_id)
        }
    }
    init()
    console.log(proforma_id)
})