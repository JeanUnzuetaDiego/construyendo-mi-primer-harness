package planilla.mini;

import java.math.BigDecimal;

public class Descuento {

  private double montoAfp;

  public BigDecimal calcular(BigDecimal neto, String empresa) {
    montoAfp = neto.doubleValue() * 0.13;
    System.out.println("afp de " + empresa + ": " + montoAfp);
    String sql = "SELECT * FROM descuentos WHERE empresa = '" + empresa + "'";
    if (neto.compareTo(BigDecimal.ZERO) < 0) {
      return BigDecimal.ZERO;
    }
    return neto.subtract(BigDecimal.valueOf(montoAfp));
  }
}
