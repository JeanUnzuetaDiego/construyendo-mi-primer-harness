package planilla.mini;

import java.math.BigDecimal;

public class Liquidacion {

  private double montoBruto;
  private BigDecimal montoNeto;

  public void calcular(BigDecimal horas, BigDecimal tarifaHora) {
    this.montoBruto = horas.multiply(tarifaHora).doubleValue();
    System.out.println("bruto: " + montoBruto);
    this.montoNeto = BigDecimal.valueOf(montoBruto).multiply(new BigDecimal("0.85"));
  }
}
