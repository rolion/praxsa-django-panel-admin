jQuery(function($){
    $(document).ready(function(){
        let bobina = null;

        function get_quantit_element(){
            return $('#id_quantity')
        }
        
        function get_id_precio_compra_mtr_lineal_element(){
            return $('#id_precio_compra_mtr_lineal')
        }

        function get_bobina_element(){
            return $('select#id_bobina')
        }
        function get_to_install_element(){
            return $('#id_to_install')
        }

        function is_bobina_selected(){
            return get_bobina_element().val() !=''
        }

        
        function get_bobina_information(){
            let bobina_id = get_bobina_element().val()
            $.ajax({
                url: '/product/bobina/'+bobina_id,
                type:"GET",
                success: function(result) {
                    bobina = result.bobina;
                    get_id_precio_compra_mtr_lineal_element().val(bobina.price)
                }
            })
        }

        $('select#id_bobina').change(function(){
            get_bobina_information()
        })
        get_quantit_element().change((e)=>{
            updateMetrosDisponibles();
        })

        function updateMetrosDisponibles(){
            let quantity = parseInt(get_quantit_element().val(), 10);
            if(bobina && $.isNumeric(quantity)) {
                let length = parseFloat(bobina.length)
                get_to_install_element().val(length * quantity);
            }
        }
        if (is_bobina_selected()){
            get_bobina_information();
        }
    })})